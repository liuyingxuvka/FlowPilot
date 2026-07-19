"""Family-level FlowPilot model-test alignment plans."""

from __future__ import annotations

import sys
from typing import Any

from flowguard import (
    FieldLifecycleGroup,
    FieldLifecyclePlan,
    FieldLifecycleRow,
    FieldProjection,
    review_field_lifecycle,
)

from flowpilot_model_test_alignment_common import *

ASSETS_PATH = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS_PATH) not in sys.path:
    sys.path.insert(0, str(ASSETS_PATH))

from flowpilot_runtime_path_evidence import (
    RuntimePathAuthority,
    attach_runtime_path_evidence_to_plan,
)
try:
    from .flowpilot_behavior_authority import (
        resolve_behavior_authority,
        selected_commitment_id,
    )
except ImportError:  # direct script execution
    from flowpilot_behavior_authority import (
        resolve_behavior_authority,
        selected_commitment_id,
    )


def _canonical_runtime_path_authority() -> RuntimePathAuthority:
    authority = resolve_behavior_authority(
        selected_commitment_id(
            "model_test_alignment_runtime_path_commitment_id"
        )
    )
    return RuntimePathAuthority(
        business_intent=authority.business_intent,
        business_intent_id=authority.business_intent_id,
        behavior_commitment_id=authority.commitment_id,
        primary_path_id=authority.primary_path_id,
        expected_terminal=authority.expected_terminal,
        surface_id=next(iter(authority.source_surface_ids), ""),
        inventory_revision=authority.inventory_revision,
    )


MTA_RUNTIME_PATH_AUTHORITY = _canonical_runtime_path_authority()


CURRENT_CARTESIAN_RISK_SHARD_OWNERS = (
    "current_contract_runtime_matrix",
    "current_contract_blocker_repair_matrix",
    "current_contract_reissue_matrix",
    "current_contract_evidence_freshness_matrix",
    "current_contract_stage_timing_matrix",
    "current_contract_overclaim_matrix",
    "current_contract_route_mutation_matrix",
    "current_contract_no_delta_repair_matrix",
    "current_contract_terminal_matrix",
)


def _cartesian_risk_shard_obligations() -> tuple[ModelObligation, ...]:
    return tuple(
        _obligation(
            f"packet_result_family.current_cartesian_risk_shard.{owner}",
            obligation_type="current_cartesian_execution_shard",
            description=(
                f"Current Cartesian owner {owner} binds its declared cells and shard ids to "
                "current external TestMesh execution proof; owned model-cell count is not test_count."
            ),
            required_test_kinds=(HAPPY, NEGATIVE),
            allow_shared_evidence=True,
            allow_shared_implementation=True,
        )
        for owner in CURRENT_CARTESIAN_RISK_SHARD_OWNERS
    )


def _cartesian_risk_shard_contracts() -> tuple[CodeContract, ...]:
    return tuple(
        _contract(
            f"packet_result_family.runner.current_cartesian_risk_shard.{owner}",
            path="simulations/run_flowpilot_current_contract_cartesian_matrix_checks.py",
            symbol="_test_mesh_report",
            implements=(f"packet_result_family.current_cartesian_risk_shard.{owner}",),
            external_inputs=("current_execution_evidence_manifest", owner),
            external_outputs=("ProofArtifactRef", "TestResultReuseTicket", "selected_and_executed_counts"),
            state_reads=("coverage_shard_ids_by_owner", "source_fingerprint"),
            error_paths=("missing_proof", "stale_proof", "progress_only", "reused_without_ticket"),
        )
        for owner in CURRENT_CARTESIAN_RISK_SHARD_OWNERS
    )


def _cartesian_risk_shard_evidence() -> tuple[TestEvidence, ...]:
    rows: list[TestEvidence] = []
    for owner in CURRENT_CARTESIAN_RISK_SHARD_OWNERS:
        obligation_id = f"packet_result_family.current_cartesian_risk_shard.{owner}"
        contract_id = f"packet_result_family.runner.current_cartesian_risk_shard.{owner}"
        rows.extend(
            (
                _evidence(
                    f"packet_result_family.happy.current_cartesian_risk_shard.{owner}",
                    test_name="test_strict_testmesh_consumes_current_proof_counts_not_model_cells",
                    path="tests/test_flowpilot_current_contract_cartesian_matrix.py",
                    command=(
                        "python -m unittest tests.test_flowpilot_current_contract_cartesian_matrix."
                        "FlowPilotCurrentContractCartesianMatrixTests."
                        "test_strict_testmesh_consumes_current_proof_counts_not_model_cells"
                    ),
                    test_kind=HAPPY,
                    covers=(obligation_id,),
                    code_contracts=(contract_id,),
                ),
                _evidence(
                    f"packet_result_family.negative.current_cartesian_risk_shard.{owner}",
                    test_name="test_strict_testmesh_rejects_reused_proof_without_ticket",
                    path="tests/test_flowpilot_current_contract_cartesian_matrix.py",
                    command=(
                        "python -m unittest tests.test_flowpilot_current_contract_cartesian_matrix."
                        "FlowPilotCurrentContractCartesianMatrixTests."
                        "test_strict_testmesh_rejects_reused_proof_without_ticket"
                    ),
                    test_kind=NEGATIVE,
                    covers=(obligation_id,),
                    code_contracts=(contract_id,),
                ),
            )
        )
    return tuple(rows)


def _with_runtime_path(plan: ModelTestAlignmentPlan, family: str) -> ModelTestAlignmentPlan:
    return attach_runtime_path_evidence_to_plan(
        plan,
        family=family,
        authority=MTA_RUNTIME_PATH_AUTHORITY,
        code_contract_prefix=f"runtime_path.{plan.model_id}",
    )


def _field_projection(
    projection_id: str,
    *,
    field_id: str,
    obligation_id: str,
    code_contract_id: str,
    required_test_kinds: tuple[str, ...],
    state_reads: tuple[str, ...] = (),
    state_writes: tuple[str, ...] = (),
    side_effects: tuple[str, ...] = (),
    error_paths: tuple[str, ...] = (),
    rationale: str,
) -> FieldProjection:
    return FieldProjection(
        projection_id=projection_id,
        field_id=field_id,
        model_obligation_id=obligation_id,
        code_contract_id=code_contract_id,
        required_test_kinds=required_test_kinds,
        state_reads=state_reads,
        state_writes=state_writes,
        side_effects=side_effects,
        error_paths=error_paths,
        risk_level="high",
        rationale=rationale,
    )


def _currentness_field_lifecycle_report(projections: tuple[FieldProjection, ...]):
    projection_by_field = {projection.field_id: projection for projection in projections}
    fields = (
        FieldLifecycleRow(
            field_id="packet.status",
            field_name="packet.status",
            locations=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
            group_id="packet_currentness",
            role="state_contract",
            lifecycle="terminal_monotonic",
            behavior_impacts=("routing_currentness", "terminal_disposition"),
            reader_ids=("_packet_is_noncurrent_for_routing", "_current_packets_for_routing"),
            writer_ids=("submit_result", "_accept_packet_result"),
            disposition="current-contract",
            projection=projection_by_field["packet.status"],
        ),
        FieldLifecycleRow(
            field_id="packet.result_ids",
            field_name="packet.result_ids",
            locations=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
            group_id="packet_currentness",
            role="state_contract",
            lifecycle="append_only_audit",
            behavior_impacts=("late_result_audit",),
            reader_ids=("render_console", "render_compact_console"),
            writer_ids=("submit_result",),
            disposition="current-contract",
            projection=projection_by_field["packet.result_ids"],
        ),
        FieldLifecycleRow(
            field_id="packet.accepted_result_id",
            field_name="packet.accepted_result_id",
            locations=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
            group_id="packet_currentness",
            role="state_contract",
            lifecycle="single_authority_pointer",
            behavior_impacts=("accepted_result_authority",),
            reader_ids=("attempt_final_closure", "render_console"),
            writer_ids=("_accept_packet_result",),
            disposition="current-contract",
            projection=projection_by_field["packet.accepted_result_id"],
        ),
        FieldLifecycleRow(
            field_id="execution_frontier.pending_route_mutation",
            field_name="execution_frontier.pending_route_mutation",
            locations=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
            group_id="frontier_currentness",
            role="state_contract",
            lifecycle="pending_until_commit",
            behavior_impacts=("route_mutation_frontier",),
            reader_ids=("render_console",),
            writer_ids=("create_route", "_advance_frontier_after_node_acceptance"),
            disposition="current-contract",
            projection=projection_by_field["execution_frontier.pending_route_mutation"],
        ),
        FieldLifecycleRow(
            field_id="active_packets",
            field_name="active_packets",
            locations=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
            group_id="derived_currentness_projection",
            role="derived_view",
            lifecycle="derived_projection",
            behavior_impacts=("compact_status", "progress_projection"),
            reader_ids=("render_compact_console", "router_next_action"),
            writer_ids=("_current_packets_for_routing",),
            disposition="current-contract",
            projection=projection_by_field["active_packets"],
        ),
        FieldLifecycleRow(
            field_id="closure_accepted_packets",
            field_name="closure_accepted_packets",
            locations=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
            group_id="derived_currentness_projection",
            role="derived_view",
            lifecycle="derived_projection",
            behavior_impacts=("final_closure", "backward_chain"),
            reader_ids=("attempt_final_closure", "_closure_blockers"),
            writer_ids=("_accepted_packets_for_closure_evidence",),
            disposition="current-contract",
            projection=projection_by_field["closure_accepted_packets"],
        ),
        FieldLifecycleRow(
            field_id="accepted_result_packets",
            field_name="accepted_result_packets",
            locations=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
            group_id="derived_currentness_projection",
            role="derived_view",
            lifecycle="derived_projection",
            behavior_impacts=("accepted_packet_lease_health", "final_return_preflight"),
            reader_ids=("accepted_packet_lease_health", "final_return_preflight"),
            writer_ids=("_accepted_result_packets_for_active_route",),
            disposition="current-contract",
            projection=projection_by_field["accepted_result_packets"],
        ),
        FieldLifecycleRow(
            field_id="route_authority_snapshot.legal_action_ids",
            field_name="route_authority_snapshot.legal_action_ids",
            locations=("skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion.py",),
            group_id="route_authority_currentness",
            role="derived_view",
            lifecycle="derived_projection",
            behavior_impacts=("route_action_selection", "wrong_path_rejection"),
            reader_ids=("_require_legal_route_action", "_reject_route_authority_submission"),
            writer_ids=("_route_authority_snapshot", "_legal_next_action_context"),
            disposition="current-contract",
            projection=projection_by_field["route_authority_snapshot.legal_action_ids"],
        ),
        FieldLifecycleRow(
            field_id="route_authority_snapshot.current_owner",
            field_name="route_authority_snapshot.current_owner",
            locations=("skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion.py",),
            group_id="route_authority_currentness",
            role="derived_view",
            lifecycle="derived_projection",
            behavior_impacts=("single_authority", "role_overreach_rejection"),
            reader_ids=("_route_authority_rejection_payload", "_write_route_authority_rejection_blocker"),
            writer_ids=("_route_authority_snapshot", "_legal_next_action_context"),
            disposition="current-contract",
            projection=projection_by_field["route_authority_snapshot.current_owner"],
        ),
        FieldLifecycleRow(
            field_id="route_authority_snapshot.required_repair_command",
            field_name="route_authority_snapshot.required_repair_command",
            locations=("skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion.py",),
            group_id="route_authority_currentness",
            role="derived_view",
            lifecycle="derived_projection",
            behavior_impacts=("repair_feedback", "corrected_retry"),
            reader_ids=("_route_authority_rejection_payload", "_reject_route_authority_submission"),
            writer_ids=("_route_authority_snapshot", "_legal_next_action_context"),
            disposition="current-contract",
            projection=projection_by_field["route_authority_snapshot.required_repair_command"],
        ),
        FieldLifecycleRow(
            field_id="active_control_blocker.route_authority_rejection",
            field_name="active_control_blocker.route_authority_rejection",
            locations=("skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion.py",),
            group_id="route_authority_currentness",
            role="state_contract",
            lifecycle="current_blocker_until_disposition",
            behavior_impacts=("wrong_path_feedback", "fallback_rejection"),
            reader_ids=("_control_blocker_summary", "_sync_control_plane_indexes"),
            writer_ids=("_write_route_authority_rejection_blocker",),
            disposition="current-contract",
            projection=projection_by_field["active_control_blocker.route_authority_rejection"],
        ),
    )
    plan = FieldLifecyclePlan(
        mesh_id="flowpilot_currentness_field_lifecycle",
        discovered_field_ids=tuple(row.field_id for row in fields),
        groups=(
            FieldLifecycleGroup(
                group_id="packet_currentness",
                boundary_kind="runtime_packet_lifecycle",
                field_ids=("packet.status", "packet.result_ids", "packet.accepted_result_id"),
                owner_route="field_lifecycle_mesh",
                rationale="Packet currentness fields decide whether result history is current authority or audit-only.",
            ),
            FieldLifecycleGroup(
                group_id="frontier_currentness",
                boundary_kind="runtime_frontier_lifecycle",
                field_ids=("execution_frontier.pending_route_mutation",),
                owner_route="field_lifecycle_mesh",
                rationale="Pending route mutation is current only until route/frontier commit.",
            ),
            FieldLifecycleGroup(
                group_id="derived_currentness_projection",
                boundary_kind="derived_runtime_view",
                field_ids=("active_packets", "accepted_result_packets", "closure_accepted_packets"),
                owner_route="model_test_alignment",
                rationale="Router active-packet views and final-closure accepted-evidence views are separate projections.",
            ),
            FieldLifecycleGroup(
                group_id="route_authority_currentness",
                boundary_kind="derived_route_authority_view",
                field_ids=(
                    "route_authority_snapshot.legal_action_ids",
                    "route_authority_snapshot.current_owner",
                    "route_authority_snapshot.required_repair_command",
                    "active_control_blocker.route_authority_rejection",
                ),
                owner_route="model_test_alignment",
                rationale="Route-authority fields derive from the current route action policy and active frontier, then become the single repair-feedback surface when a wrong path is rejected.",
            ),
        ),
        fields=fields,
        claim_scope="currentness_field_family",
        allow_scoped_confidence=False,
        notes="Current-contract only; no legacy aliases, fallbacks, or historical promotion.",
    )
    return review_field_lifecycle(plan)



def build_alignment_plan_entries() -> list[dict[str, Any]]:
    """Build major FlowPilot model/test-family alignment plans."""

    startup = ModelTestAlignmentPlan(
        model_id="startup",
        obligations=(
            _obligation(
                "startup.questions.pause_before_work",
                obligation_type="contract",
                description="Startup asks for the work request and background-collaboration permission, waits for the answer, and blocks banner/controller work until the answer boundary is satisfied.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "startup.run_isolation_and_activation",
                obligation_type="scenario",
                description="Startup creates prompt-isolated current-run state, rejects legacy reviewer/PM startup role gates, and continues through the current Runtime/Router packet path.",
                required_test_kinds=(HAPPY, FAILURE),
            ),
        ),
        test_evidence=(
            _evidence(
                "startup.happy.prompt_isolated_run",
                test_name="test_startup_sequence_creates_prompt_isolated_run",
                path="tests/router_runtime/startup_bootstrap.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=HAPPY,
                covers=("startup.run_isolation_and_activation",),
            ),
            _evidence(
                "startup.negative.waits_for_answers",
                test_name="test_startup_waits_for_answers_before_banner_or_controller",
                path="tests/router_runtime/startup_bootstrap.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=NEGATIVE,
                covers=("startup.questions.pause_before_work",),
            ),
            _evidence(
                "startup.happy.native_intake_boundary",
                test_name="test_startup_intake_controller_receipt_folds_native_ui_result",
                path="tests/router_runtime/startup_bootstrap.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=HAPPY,
                covers=("startup.questions.pause_before_work",),
            ),
            _evidence(
                "startup.failure.legacy_role_gates_unsupported",
                test_name="test_startup_old_role_gate_events_are_unsupported",
                path="tests/router_runtime/startup_bootstrap.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=FAILURE,
                covers=("startup.run_isolation_and_activation",),
            ),
        ),
    )

    packet_card_ack = ModelTestAlignmentPlan(
        model_id="packet_card_ack",
        obligations=(
            _obligation(
                "packet.physical_body_boundary",
                obligation_type="contract",
                description="Packet envelopes, bodies, result files, hashes, and recipient reads stay physically separated from Controller relay text.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "card.ack_identity_and_bundle",
                obligation_type="hazard",
                description="Card and bundle ACKs require correct role, token, receipt, hash, and per-card completion before advancing.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "ack.return_wait_preconsumption",
                obligation_type="transition",
                description="Router preconsumes valid ACK/return events and blocks incomplete or invalid pre-ACK reports without advancing stale waits.",
                required_test_kinds=(EDGE, FAILURE),
            ),
            _obligation(
                "packet_control_plane.facade_split_integrity",
                obligation_type="contract",
                description="Packet control-plane model keeps its facade import path while state, transition, and invariant owners remain executable.",
                required_test_kinds=(HAPPY,),
            ),
        ),
        test_evidence=(
            _evidence(
                "packet.happy.physical_files",
                test_name="test_pm_issue_writes_physical_envelope_body_and_ledger",
                path="tests/test_flowpilot_packet_runtime.py",
                command="python -m unittest tests.test_flowpilot_packet_runtime",
                test_kind=HAPPY,
                covers=("packet.physical_body_boundary",),
            ),
            _evidence(
                "packet.negative.controller_body_exclusion",
                test_name="test_controller_handoff_contains_envelope_only_not_body_content",
                path="tests/test_flowpilot_packet_runtime.py",
                command="python -m unittest tests.test_flowpilot_packet_runtime",
                test_kind=NEGATIVE,
                covers=("packet.physical_body_boundary",),
            ),
            _evidence(
                "card.happy.card_ack",
                test_name="test_card_runtime_opens_card_and_submits_ack",
                path="tests/test_flowpilot_card_runtime.py",
                command="python -m pytest tests/test_flowpilot_card_runtime.py",
                test_kind=HAPPY,
                covers=("card.ack_identity_and_bundle",),
            ),
            _evidence(
                "card.negative.wrong_role_ack",
                test_name="test_card_runtime_rejects_wrong_role_and_ack_without_receipt",
                path="tests/test_flowpilot_card_runtime.py",
                command="python -m pytest tests/test_flowpilot_card_runtime.py",
                test_kind=NEGATIVE,
                covers=("card.ack_identity_and_bundle",),
            ),
            _evidence(
                "ack.edge.preconsume_valid_ack",
                test_name="test_router_daemon_tick_consumes_card_ack_without_manual_next",
                path="tests/router_runtime/ack_return.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_ack_return",
                test_kind=EDGE,
                covers=("ack.return_wait_preconsumption",),
            ),
            _evidence(
                "ack.failure.incomplete_bundle",
                test_name="test_router_daemon_incomplete_bundle_ack_waits_without_advancing",
                path="tests/router_runtime/ack_return.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_ack_return",
                test_kind=FAILURE,
                covers=("ack.return_wait_preconsumption",),
            ),
            _evidence(
                "packet_control_plane.happy.split_runner",
                test_name="run_packet_control_plane_checks",
                path="skills/flowpilot/assets/run_packet_control_plane_checks.py",
                command="python skills/flowpilot/assets/run_packet_control_plane_checks.py",
                test_kind=HAPPY,
                covers=("packet_control_plane.facade_split_integrity",),
            ),
        ),
    )

    packet_result_family = ModelTestAlignmentPlan(
        model_id="packet_result_family",
        obligations=(
            _obligation(
                "packet_result_family.research.durable_event_fold",
                obligation_type="transition",
                description="Research batches fold durable result envelopes into worker_research_report_returned before stale waits.",
                required_test_kinds=(HAPPY,),
            ),
            _obligation(
                "packet_result_family.research.partial_member_wait",
                obligation_type="scenario",
                description="Partial research batches name only missing worker roles and keep completed members out of reminders.",
                required_test_kinds=(EDGE,),
            ),
            _obligation(
                "packet_result_family.research.recipient_and_sealed_boundary",
                obligation_type="hazard",
                description="Wrong-recipient research result envelopes do not satisfy family completion.",
                required_test_kinds=(NEGATIVE,),
            ),
            _obligation(
                "packet_result_family.current_node.durable_event_fold",
                obligation_type="transition",
                description="Current-node batches fold durable result envelopes into worker_current_node_result_returned before stale waits.",
                required_test_kinds=(HAPPY,),
            ),
            _obligation(
                "packet_result_family.current_node.partial_member_wait",
                obligation_type="scenario",
                description="Mixed manual/durable current-node batches record only missing result-return evidence.",
                required_test_kinds=(EDGE,),
            ),
            _obligation(
                "packet_result_family.current_node.recipient_and_sealed_boundary",
                obligation_type="hazard",
                description="Wrong-recipient current-node result envelopes do not satisfy family completion.",
                required_test_kinds=(NEGATIVE,),
            ),
            _obligation(
                "packet_result_family.pm_role_work.durable_event_fold",
                obligation_type="transition",
                description="PM role-work batches fold durable FlowGuard operator result envelopes into role_work_result_returned before stale waits.",
                required_test_kinds=(HAPPY,),
            ),
            _obligation(
                "packet_result_family.pm_role_work.partial_member_wait",
                obligation_type="scenario",
                description="Partial PM role-work batches name only missing FlowGuard operator roles and keep completed members out of reminders.",
                required_test_kinds=(EDGE,),
            ),
            _obligation(
                "packet_result_family.pm_role_work.recipient_and_sealed_boundary",
                obligation_type="hazard",
                description="PM role-work result envelopes reject wrong next_recipient values at the result boundary.",
                required_test_kinds=(NEGATIVE,),
            ),
            _obligation(
                "packet_result_family.flowguard_current_report_before_reviewer",
                obligation_type="mechanical_consistency_contract",
                description=(
                    "FlowGuard top-level passed status, contract self-check, "
                    "and child hard evidence consistency must agree before a "
                    "FlowGuard work order can pass or release a Reviewer packet."
                ),
                required_test_kinds=(HAPPY, NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.flowguard_artifact_hard_decision_before_reviewer",
                obligation_type="artifact_payload_contract",
                description=(
                    "Packet-owned run-local flowguard_evidence.json hard decisions "
                    "must be folded into FlowGuard result acceptance, work-order "
                    "decision, and Reviewer evidence exposure."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.flowguard_repair_blocker_identity_continuity",
                obligation_type="field_identity_contract",
                description=(
                    "repair_blocker_id must stay continuous from repaired subject packet "
                    "to FlowGuard packet, FlowGuard work order, and Reviewer manifest."
                ),
                required_test_kinds=(NEGATIVE, EDGE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.flowguard_semantic_recheck_subject_bound",
                obligation_type="external_result_contract_profile",
                description=(
                    "Blocker-bound FlowGuard rechecks must prove authorized subject-result "
                    "consumption and subject-bound semantic coverage from the current packet's "
                    "structured result contract profile binding, and reject shape-only or "
                    "current-contract-only passes."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.reviewer_blocks_shallow_flowguard_depth",
                obligation_type="review_gate_contract",
                description=(
                    "Reviewer must block a mechanically passed FlowGuard report when it only "
                    "proves field shape, current-contract mechanics, role boundary, packet "
                    "presence, or generic process form instead of target-specific depth."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.flowguard_semantic_recheck_ai_facing_projection",
                obligation_type="ai_facing_contract_projection",
                description=(
                    "AI-facing FlowGuard semantic recheck packets must project the profile-bound "
                    "required fields, finite allowed values, field type requirements, forbidden aliases, "
                    "and minimal valid shape before the FlowGuard operator submits a result."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.flowguard_semantic_recheck_corrected_retry_convergence",
                obligation_type="fake_ai_repair_convergence",
                description=(
                    "Near-synonym or wrong finite-value semantic_recheck payloads must be rejected "
                    "with current-contract feedback, then a corrected second-round payload must return "
                    "to the ordinary accepted path without GlassBreak."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.contract_driven_fake_ai_cartesian_retry",
                obligation_type="contract_driven_fake_ai_cartesian_replay",
                description=(
                    "A deterministic fake-AI responder must read packet-local contracts, refuse to "
                    "guess missing finite options, generate wrong-value rows for every visible "
                    "allowed_value_options field, and repair each row from runtime's reissue feedback "
                    "before the GlassBreak threshold."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.fake_ai_runtime_replay_matrix_closure",
                obligation_type="runtime_replay_testmesh_contract",
                description=(
                    "Generated fake-AI contract cells must be promoted into a runtime replay matrix "
                    "that names the expected reject/reissue/repair/GlassBreak reaction and links each "
                    "class to concrete runtime tests rather than stopping at generated bad payloads."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.control_plane_ledger_hygiene_cartesian_matrix",
                obligation_type="runtime_control_plane_cartesian_contract",
                description=(
                    "Fake-AI replay must materialize the full control-plane ledger hygiene Cartesian "
                    "product across result status, accepted pointer state, repair identity, packet "
                    "family, blocker state, break-glass state, Reviewer authorization, and closure "
                    "phase; every cell must name the mechanical runtime reaction and evidence owner."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.real_issue_backfeed_registry_bridge",
                obligation_type="real_issue_backfeed_contract",
                description=(
                    "Every newly discovered real control-plane issue family must be backfed as a "
                    "public-reference row with fake-AI profile, contract cell, Cartesian row, expected "
                    "runtime reaction, replay suite owner, and no copied sealed body."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.sealed_body_related_context_reads",
                obligation_type="authorized_body_read_contract",
                description=(
                    "Blocker, repair, review, and FlowGuard handoffs must authorize the assigned "
                    "downstream role to open the blocker result body plus related upstream result "
                    "bodies before submit."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.clean_e2e_authorized_material_openings",
                obligation_type="current_run_authorized_material_proof",
                description=(
                    "Clean fake E2E runs must prove that every packet declaring required "
                    "authorized result-body reads opened those bodies through the assigned-role "
                    "packet path before result submission."
                ),
                required_test_kinds=(REPLAY,),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.pm_repair_evidence_obligation_lifecycle",
                obligation_type="repair_obligation_contract",
                description=(
                    "PM repair packets must carry blocker-derived repair_evidence_obligations; "
                    "PM results must disposition every obligation; repair packets and FlowGuard "
                    "semantic rechecks must consume the resulting obligation context."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.flowguard_reissue_preserves_current_evidence_policy",
                obligation_type="field_lifecycle_contract",
                description=(
                    "Mechanical reissue of a FlowGuard packet must preserve blocker identity, "
                    "semantic recheck fields, required subject artifacts, and evidence_output_policy "
                    "while retargeting the evidence root to the fresh packet id."
                ),
                required_test_kinds=(NEGATIVE, EDGE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.flowguard_reissue_preserves_required_authorized_result_reads",
                obligation_type="field_lifecycle_contract",
                description=(
                    "All current FlowGuard reissue paths must preserve the source packet's "
                    "required authorized result-body reads so the FlowGuard operator must open "
                    "the same material before submitting the replacement result. Leaf obligations "
                    "own the separate ordinary-reissue and semantic-recheck edge evidence."
                ),
                required_test_kinds=(NEGATIVE,),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.flowguard_standard_reissue_preserves_required_authorized_result_reads",
                obligation_type="field_lifecycle_contract",
                description=(
                    "Ordinary mechanical FlowGuard reissue must copy required authorized "
                    "result-body reads into the fresh envelope, body, and current handoff contract."
                ),
                required_test_kinds=(EDGE,),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.flowguard_semantic_recheck_reissue_preserves_required_authorized_result_reads",
                obligation_type="field_lifecycle_contract",
                description=(
                    "Semantic-recheck FlowGuard reissue must preserve required authorized "
                    "result-body reads while also retaining blocker-bound semantic recheck context."
                ),
                required_test_kinds=(EDGE,),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.review_handoff_blocks_empty_required_flowguard_manifest",
                obligation_type="handoff_contract",
                description=(
                    "When a subject packet requires FlowGuard, Reviewer packets cannot be issued "
                    "with an empty matching FlowGuard evidence manifest; runtime records a repairable "
                    "control-plane blocker before review."
                ),
                required_test_kinds=(NEGATIVE,),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.repair_loop_glass_break_root_cause_identity",
                obligation_type="liveness_contract",
                description=(
                    "Repeated no-delta repair blockers for the same FlowGuard evidence-chain root "
                    "must count toward BreakGlass even when the surface gate changes."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.historical_failure_families_have_normal_repair_routes",
                obligation_type="historical_failure_contract",
                description=(
                    "Historical missing-body, missing-mail, wrong-address, stale-context, "
                    "vanished-evidence, install split-brain, invalid repair-target, and repeated-blocker "
                    "families must name a normal repair route before they can support confidence."
                ),
                required_test_kinds=(REPLAY,),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.glass_break_is_alarm_not_success_path",
                obligation_type="liveness_contract",
                description=(
                    "BreakGlass must remain an alarm for unrepaired repeated blockers; accepted "
                    "FlowPilot rehearsals cannot treat reaching BreakGlass as a successful path."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.contract_exhaustion_matrix_owners_are_child_suites",
                obligation_type="testmesh_handoff_contract",
                description=(
                    "Every required contract-exhaustion evidence owner emitted by the matrix "
                    "must be registered as a current TestMesh child suite so generated rows "
                    "cannot pass without downstream consumption."
                ),
                required_test_kinds=(REPLAY,),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.cartesian_control_plane_cells_have_oracles",
                obligation_type="cartesian_exhaustion_contract",
                description=(
                    "Every declared control-plane material, mutation, handoff context, and "
                    "downstream consumer combination must be either explicitly skipped with "
                    "a reason or mapped to a current-contract repair oracle, evidence owner, "
                    "and normal-vs-GlassBreak recovery expectation."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.integration_cartesian_coverage_keeps_pm_optimization_boundary",
                obligation_type="prompt_workflow_integration_cartesian_contract",
                description=(
                    "PM-owned system-integration coverage must exercise stage, role, artifact-family, "
                    "failure-class, severity, authority, and evidence-timing combinations while keeping "
                    "hard composition failures repairable through existing PM/review/FlowGuard paths and "
                    "keeping advisory cohesion improvements out of runtime semantic hard blockers."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.pointer_persistence_hardening",
                obligation_type="runtime_entry_contract",
                description=(
                    "FlowPilot current/index pointers use the runtime JSON gateway for atomic persistence "
                    "and recover only from unambiguous current-run evidence."
                ),
                required_test_kinds=(NEGATIVE, EDGE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.submit_result_body_entry_hardening",
                obligation_type="runtime_entry_contract",
                description=(
                    "FlowPilot submit-result validates exactly one top-level JSON object body source "
                    "before loading or mutating the ledger."
                ),
                required_test_kinds=(NEGATIVE, EDGE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.stage_evidence_matrix_all_families",
                obligation_type="stage_evidence_contract",
                description=(
                    "Every current packet/result family has exactly one stage-evidence matrix row, "
                    "and every generated packet handoff exposes that row through the single envelope "
                    "handoff authority and its open-packet checklist projection so roles know which "
                    "evidence is due now and which evidence is future-stage only."
                ),
                required_test_kinds=(HAPPY, NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.current_handoff_checklist_single_authority",
                obligation_type="single_authority_contract",
                description=(
                    "Mechanical result requirements live only in current_handoff_contract.v2 and the "
                    "fingerprinted submission_checklist.v2 projection; sealed packet bodies, reissue "
                    "diagnostics, remembered registries, and private minimal-shape helpers cannot act "
                    "as an alternate result authority."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.strict_fake_ai_open_packet_identity",
                obligation_type="fake_ai_identity_contract",
                description=(
                    "Canonical fake AI consumes only a current open-packet result and rejects missing "
                    "ACK/material delivery, stale run/packet/lease/route/source identities, tampered "
                    "fingerprints, unknown families, wrong roles, and body/checklist conflicts."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.formal_execution_covering_array_receipts",
                obligation_type="execution_coverage_contract",
                description=(
                    "The finite AI response universe enumerates every registered family minimum, "
                    "top-level required omission, and forbidden path, then executes deterministic "
                    "pairwise and critical three-way public submit rows with passed/failed/not-run "
                    "receipts kept distinct."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.testmesh_requires_fingerprinted_proof",
                obligation_type="testmesh_evidence_truth_contract",
                description=(
                    "Acceptance TestMesh children cannot declare hand-written passed/current rows; "
                    "each passing child supplies command, result path, exit code, selected/executed "
                    "count, covered obligations, and a current SHA-256 ProofArtifactRef."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.dynamic_pm_repair_owner_projection",
                obligation_type="dynamic_contract_projection",
                description=(
                    "Terminal PM repair checklist branches project every current active acceptance "
                    "item onto a route owner and supplemental repair item before fake or real PM "
                    "submission, so adding an acceptance item cannot create an endless mechanical loop."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "packet_result_family.portable_runtime_self_check_receipt",
                obligation_type="install_portability_contract",
                description=(
                    "FlowPilot start_run records an installed-skill runtime self-check receipt and "
                    "must not require arbitrary target projects to contain FlowPilot development-repo "
                    "simulation scripts."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            *_cartesian_risk_shard_obligations(),
        ),
        code_contracts=(
            _contract(
                "packet_result_family.runtime.stage_evidence_matrix",
                path="skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py",
                symbol="PACKET_STAGE_EVIDENCE_MATRIX",
                implements=("packet_result_family.stage_evidence_matrix_all_families",),
                external_inputs=("contract_family_id",),
                external_outputs=("stage_evidence_row",),
                state_reads=("packet_result_contract_family_id",),
            ),
            _contract(
                "packet_result_family.runtime.current_handoff_stage_matrix",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_build_current_handoff_contract",
                implements=("packet_result_family.stage_evidence_matrix_all_families",),
                external_inputs=("ledger", "packet_envelope", "authorized_result_reads"),
                external_outputs=("current_handoff_contract.stage_evidence_matrix",),
                state_reads=("packet_result_contract_family_id", "packet_stage_evidence_matrix"),
                state_writes=("packet.envelope.current_handoff_contract",),
            ),
            _contract(
                "packet_result_family.runtime.current_handoff_checklist_projection",
                path="skills/flowpilot/assets/flowpilot_new_role_commands.py",
                symbol="_submission_checklist_from_current_handoff_contract",
                implements=("packet_result_family.current_handoff_checklist_single_authority",),
                external_inputs=("current_handoff_contract.v2", "opened_materials", "current_identity"),
                external_outputs=("submission_checklist.v2",),
                state_reads=("current_handoff_contract.required_report_contract", "review_window"),
            ),
            _contract(
                "packet_result_family.fake_ai.from_open_packet_result",
                path="simulations/flowpilot_contract_driven_fake_ai.py",
                symbol="ContractDrivenFakeAI.from_open_packet_result",
                implements=("packet_result_family.strict_fake_ai_open_packet_identity",),
                external_inputs=("open_packet_result.v1",),
                external_outputs=("strict_current_result_payload",),
                state_reads=("submission_checklist.v2", "current_handoff_contract.v2", "review_window"),
            ),
            _contract(
                "packet_result_family.formal_ai_execution_closure",
                path="simulations/flowpilot_ai_response_execution_closure_model.py",
                symbol="run_execution_closure",
                implements=("packet_result_family.formal_execution_covering_array_receipts",),
                external_inputs=("finite_contract_universe", "covering_array_mode"),
                external_outputs=("execution_receipts", "test_mesh_receipt"),
                state_reads=("packet_result_contract_registry",),
            ),
            _contract(
                "packet_result_family.acceptance_testmesh_proof_binding",
                path="simulations/flowpilot_acceptance_testmesh_model.py",
                symbol="build_testmesh_plan",
                implements=("packet_result_family.testmesh_requires_fingerprinted_proof",),
                external_inputs=("current_proof_manifest",),
                external_outputs=("proof_required_testmesh_plan",),
                state_reads=("ProofArtifactRef", "selected_and_executed_counts"),
            ),
            _contract(
                "packet_result_family.runtime.dynamic_pm_repair_contract",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_project_current_pm_repair_contract",
                implements=("packet_result_family.dynamic_pm_repair_owner_projection",),
                external_inputs=("current_blocker", "active_acceptance_items"),
                external_outputs=("current_pm_repair_branch_shapes",),
                state_reads=("active_blockers", "acceptance_item_registry", "terminal_supplemental_repair"),
            ),
            _contract(
                "packet_result_family.runtime.flowguard_stage_matrix",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_ensure_flowguard_packet_for_task_result",
                implements=("packet_result_family.stage_evidence_matrix_all_families",),
                external_inputs=("ledger", "subject_packet", "subject_result"),
                external_outputs=("flowguard_packet.subject_stage_evidence_matrix",),
                state_reads=("subject_packet", "packet_stage_evidence_matrix"),
                state_writes=("flowguard_packet",),
            ),
            _contract(
                "packet_result_family.runtime.reviewer_stage_matrix",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_ensure_review_packet_for_task_result",
                implements=("packet_result_family.stage_evidence_matrix_all_families",),
                external_inputs=("ledger", "subject_packet_id"),
                external_outputs=("review_packet.subject_stage_evidence_matrix",),
                state_reads=("subject_packet", "packet_stage_evidence_matrix", "flowguard_manifest"),
                state_writes=("review_packet",),
            ),
            _contract(
                "packet_result_family.runtime.portable_self_check",
                path="skills/flowpilot/assets/flowpilot_runtime_self_check.py",
                symbol="runtime_self_check",
                implements=("packet_result_family.portable_runtime_self_check_receipt",),
                external_inputs=("assets_root",),
                external_outputs=("runtime_self_check_receipt",),
                state_reads=("installed_skill_assets", "flowguard_package"),
            ),
            _contract(
                "packet_result_family.runtime.record_portable_self_check",
                path="skills/flowpilot/assets/flowpilot_new_shared.py",
                symbol="_record_runtime_self_check_receipt",
                implements=("packet_result_family.portable_runtime_self_check_receipt",),
                external_inputs=("run_shell",),
                external_outputs=("run_root.runtime.flowpilot_runtime_self_check_receipt.json",),
                state_writes=("ledger.flowpilot_runtime_self_check",),
            ),
            _contract(
                "packet_result_family.runtime.flowguard_current_report_gate",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_flowguard_current_report_violation",
                implements=(
                    "packet_result_family.flowguard_current_report_before_reviewer",
                    "packet_result_family.flowguard_artifact_hard_decision_before_reviewer",
                    "packet_result_family.flowguard_semantic_recheck_subject_bound",
                ),
                external_inputs=("ledger", "packet", "result"),
                external_outputs=("contract_check",),
                state_reads=("flowguard_result_body", "flowguard_evidence_artifact"),
            ),
            _contract(
                "packet_result_family.runtime.flowguard_artifact_hard_decision",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_flowguard_packet_artifact_hard_decision",
                implements=("packet_result_family.flowguard_artifact_hard_decision_before_reviewer",),
                external_inputs=("ledger", "flowguard_packet"),
                external_outputs=("hard_evidence_decision", "hard_evidence_source_path"),
                state_reads=("run_root", "packet_body.evidence_output_policy"),
            ),
            _contract(
                "packet_result_family.runtime.flowguard_semantic_recheck_gate",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_flowguard_semantic_recheck_contract_violation",
                implements=(
                    "packet_result_family.flowguard_semantic_recheck_subject_bound",
                    "packet_result_family.pm_repair_evidence_obligation_lifecycle",
                    "packet_result_family.flowguard_semantic_recheck_corrected_retry_convergence",
                ),
                external_inputs=("flowguard_packet", "flowguard_result_payload"),
                external_outputs=("contract_check",),
                state_reads=(
                    "packet.envelope.result_contract_profile_bindings",
                    "packet_body.semantic_recheck_contract.context_only",
                    "flowguard_result.semantic_recheck",
                ),
            ),
            _contract(
                "packet_result_family.runtime.review_packet_flowguard_depth_instruction",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_ensure_review_packet_for_task_result",
                implements=("packet_result_family.reviewer_blocks_shallow_flowguard_depth",),
                external_inputs=("ledger", "subject_packet", "matching_flowguard_result"),
                external_outputs=("review_packet_instruction", "authorized_result_reads"),
                state_reads=("flowguard_evidence_manifest", "flowguard_result_body"),
            ),
            _contract(
                "packet_result_family.prompt.reviewer_shallow_flowguard_depth_card",
                path="skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md",
                symbol="reviewer.core",
                implements=("packet_result_family.reviewer_blocks_shallow_flowguard_depth",),
                external_inputs=("review_packet", "matching_flowguard_result"),
                external_outputs=("reviewer_blocker", "pm_suggestion_items"),
                state_reads=("authorized_subject_result", "flowguard_result_body"),
            ),
            _contract(
                "packet_result_family.simulation.fake_e2e_shallow_flowguard_reviewer_block",
                path="skills/flowpilot/assets/flowpilot_core_runtime/fake_e2e.py",
                symbol="run_fake_e2e",
                implements=("packet_result_family.reviewer_blocks_shallow_flowguard_depth",),
                external_inputs=("inject_shallow_flowguard_report", "inject_contract_faults"),
                external_outputs=("reviewer_shallow_flowguard_blocks", "pm_repair_packet"),
                state_reads=("review_packet.authorized_result_reads", "flowguard_result_body"),
            ),
            _contract(
                "packet_result_family.runtime.effective_result_contract_profiles",
                path="skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py",
                symbol="effective_result_contract_from_envelope",
                implements=("packet_result_family.flowguard_semantic_recheck_ai_facing_projection",),
                external_inputs=("packet_envelope.result_contract_profile_ids", "packet_envelope.result_contract_profile_bindings"),
                external_outputs=("effective_required_fields", "effective_allowed_value_options", "effective_minimal_valid_shape"),
                state_reads=("packet_stage_evidence_matrix.RESULT_CONTRACT_PROFILES",),
            ),
            _contract(
                "packet_result_family.runtime.current_handoff_result_profile_contract",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_build_current_handoff_contract",
                implements=("packet_result_family.flowguard_semantic_recheck_ai_facing_projection",),
                external_inputs=("ledger", "packet_envelope", "authorized_result_reads"),
                external_outputs=("current_handoff_contract.required_report_contract",),
                state_reads=("packet_envelope.result_contract_profile_bindings", "effective_result_contract"),
                state_writes=("packet.envelope.current_handoff_contract", "packet.body.current_handoff_contract"),
            ),
            _contract(
                "packet_result_family.runtime.current_contract_reissue_feedback",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_block_result_and_reissue_current_packet_family",
                implements=(
                    "packet_result_family.flowguard_semantic_recheck_ai_facing_projection",
                    "packet_result_family.flowguard_semantic_recheck_corrected_retry_convergence",
                ),
                external_inputs=("blocked_packet", "blocked_result", "contract_check"),
                external_outputs=("current_contract_reissue_packet.body"),
                state_reads=("effective_result_contract", "contract_check.missing_required_fields", "contract_check.forbidden_fields_seen"),
                state_writes=("fresh_packet.envelope.result_contract_profile_bindings", "fresh_packet.body.minimal_valid_shape"),
            ),
            _contract(
                "packet_result_family.simulation.contract_driven_fake_ai_responder",
                path="simulations/flowpilot_contract_driven_fake_ai.py",
                symbol="ContractDrivenFakeAIResponder",
                implements=(
                    "packet_result_family.flowguard_semantic_recheck_ai_facing_projection",
                    "packet_result_family.flowguard_semantic_recheck_corrected_retry_convergence",
                    "packet_result_family.contract_driven_fake_ai_cartesian_retry",
                    "packet_result_family.fake_ai_runtime_replay_matrix_closure",
                ),
                external_inputs=(
                    "packet.body.current_handoff_contract.required_report_contract",
                    "reissue_packet.body.allowed_value_options",
                    "reissue_packet.body.minimal_valid_shape",
                ),
                external_outputs=("legal_payload", "invalid_allowed_value_payload", "repaired_payload"),
                state_reads=("packet_local_contract_projection",),
            ),
            _contract(
                "packet_result_family.model.fake_ai_runtime_replay_matrix",
                path="simulations/flowpilot_fake_ai_runtime_replay_model.py",
                symbol="runtime_replay_cells",
                implements=(
                    "packet_result_family.fake_ai_runtime_replay_matrix_closure",
                    "packet_result_family.control_plane_ledger_hygiene_cartesian_matrix",
                ),
                external_inputs=(
                    "contract_driven_fake_ai.coverage_cells",
                    "review_window_fake_ai_cells",
                    "control_plane_ledger_hygiene_axes",
                ),
                external_outputs=("runtime_replay_cells",),
                state_reads=("packet_result_contracts", "review_window_contracts"),
            ),
            _contract(
                "packet_result_family.runner.fake_ai_runtime_replay_checks",
                path="simulations/run_flowpilot_fake_ai_runtime_replay_checks.py",
                symbol="run_checks",
                implements=(
                    "packet_result_family.fake_ai_runtime_replay_matrix_closure",
                    "packet_result_family.control_plane_ledger_hygiene_cartesian_matrix",
                ),
                external_inputs=("runtime_replay_cells",),
                external_outputs=("flowguard_report", "hazard_report", "matrix_report"),
                state_reads=("flowguard_model",),
            ),
            _contract(
                "packet_result_family.model.real_issue_backfeed_registry",
                path="simulations/flowpilot_real_issue_backfeed.py",
                symbol="backfeed_rows",
                implements=("packet_result_family.real_issue_backfeed_registry_bridge",),
                external_inputs=("public_issue_reference",),
                external_outputs=("backfeed_rows", "backfeed_cells"),
                state_reads=("runtime_replay_suite_owner",),
            ),
            _contract(
                "packet_result_family.runtime.blocker_related_authorized_reads",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_blocker_authorized_result_reads",
                implements=("packet_result_family.sealed_body_related_context_reads",),
                external_inputs=("ledger", "active_blocker"),
                external_outputs=("authorized_result_reads",),
                state_reads=("active_blocker.result_id", "active_blocker.target_result_id", "upstream_packet.authorized_result_reads"),
                state_writes=("packet.envelope.authorized_result_reads", "packet.body.current_handoff_contract"),
            ),
            _contract(
                "packet_result_family.simulation.fake_e2e_authorized_material_proof",
                path="skills/flowpilot/assets/flowpilot_core_runtime/fake_e2e.py",
                symbol="run_fake_e2e",
                implements=("packet_result_family.clean_e2e_authorized_material_openings",),
                external_inputs=("clean_current_run_packets", "authorized_result_reads"),
                external_outputs=("authorized_input_openings",),
                state_reads=("packet.envelope.authorized_result_reads", "packet.authorized_result_read_receipts"),
            ),
            _contract(
                "packet_result_family.runtime.pm_repair_obligation_disposition_gate",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_pm_repair_obligation_disposition_violation",
                implements=("packet_result_family.pm_repair_evidence_obligation_lifecycle",),
                external_inputs=("pm_repair_packet", "pm_repair_result_payload"),
                external_outputs=("contract_check",),
                state_reads=("pm_repair_packet.body.repair_evidence_obligations", "pm_repair_result.repair_obligation_disposition"),
            ),
            _contract(
                "packet_result_family.runtime.repair_obligation_context_projection",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_attach_repair_obligation_context_to_packet",
                implements=("packet_result_family.pm_repair_evidence_obligation_lifecycle",),
                external_inputs=("ledger", "repair_packet", "active_blocker", "pm_repair_decision_id"),
                external_outputs=("repair_packet_body"),
                state_reads=("pm_repair_decision.repair_obligation_disposition",),
                state_writes=("repair_packet.body.repair_obligation_context",),
            ),
            _contract(
                "packet_result_family.runtime.flowguard_reissue_inherited_body_payload",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_flowguard_reissue_inherited_body_payload",
                implements=("packet_result_family.flowguard_reissue_preserves_current_evidence_policy",),
                external_inputs=("ledger", "blocked_flowguard_packet", "fresh_packet_id"),
                external_outputs=("reissue_body_fields",),
                state_reads=("blocked_flowguard_packet.body", "ledger.run_root"),
                state_writes=("fresh_flowguard_packet.body.evidence_output_policy",),
            ),
            _contract(
                "packet_result_family.runtime.flowguard_reissue_inherited_authorized_reads",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_flowguard_reissue_inherited_authorized_result_reads",
                implements=(
                    "packet_result_family.flowguard_reissue_preserves_required_authorized_result_reads",
                    "packet_result_family.flowguard_standard_reissue_preserves_required_authorized_result_reads",
                    "packet_result_family.flowguard_semantic_recheck_reissue_preserves_required_authorized_result_reads",
                ),
                external_inputs=("ledger", "blocked_flowguard_packet"),
                external_outputs=("authorized_result_reads",),
                state_reads=(
                    "blocked_flowguard_packet.envelope.authorized_result_reads",
                    "blocked_flowguard_packet.envelope.current_handoff_contract",
                ),
                state_writes=(
                    "fresh_flowguard_packet.envelope.authorized_result_reads",
                    "fresh_flowguard_packet.body.authorized_result_reads",
                    "fresh_flowguard_packet.current_handoff_contract",
                ),
            ),
            _contract(
                "packet_result_family.runtime.flowguard_reissue_issue_task_packet_reads",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_block_result_and_reissue_current_packet_family",
                implements=(
                    "packet_result_family.flowguard_reissue_preserves_required_authorized_result_reads",
                    "packet_result_family.flowguard_standard_reissue_preserves_required_authorized_result_reads",
                    "packet_result_family.flowguard_semantic_recheck_reissue_preserves_required_authorized_result_reads",
                ),
                external_inputs=("ledger", "blocked_flowguard_packet", "mechanically_blocked_result"),
                external_outputs=("fresh_flowguard_packet_id",),
                state_reads=("reissue_authorized_result_reads",),
                state_writes=("issue_task_packet.authorized_result_reads",),
            ),
            _contract(
                "packet_result_family.runtime.flowguard_packet_issue_inherits_blocker",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_ensure_flowguard_packet_for_task_result",
                implements=(
                    "packet_result_family.flowguard_repair_blocker_identity_continuity",
                    "packet_result_family.flowguard_semantic_recheck_subject_bound",
                ),
                external_inputs=("ledger", "subject_packet", "subject_result"),
                external_outputs=("flowguard_packet_id",),
                state_reads=("subject_packet.repair_blocker_id", "active_blockers"),
                state_writes=(
                    "flowguard_packet.repair_blocker_id",
                    "flowguard_packet.envelope.result_contract_profile_ids",
                    "flowguard_packet.envelope.result_contract_profile_bindings",
                    "flowguard_packet.body.semantic_recheck_contract.context_only",
                ),
            ),
            _contract(
                "packet_result_family.runtime.repair_blocker_identity_formal_gate",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_formal_repair_identity_blockers",
                implements=("packet_result_family.flowguard_repair_blocker_identity_continuity",),
                external_inputs=("packet",),
                external_outputs=("mechanical_blockers",),
                state_reads=(
                    "packet.repair_blocker_id",
                    "packet.envelope.repair_blocker_id",
                    "packet.body.current_handoff_contract",
                ),
            ),
            _contract(
                "packet_result_family.runtime.flowguard_work_order_hard_decision",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_record_flowguard_from_packet_result",
                implements=(
                    "packet_result_family.flowguard_artifact_hard_decision_before_reviewer",
                    "packet_result_family.flowguard_repair_blocker_identity_continuity",
                ),
                external_inputs=("ledger", "flowguard_packet", "flowguard_result"),
                external_outputs=("flowguard_work_order_id",),
                state_reads=("flowguard_evidence_artifact", "flowguard_packet.repair_blocker_id"),
                state_writes=("flowguard_work_order.decision", "flowguard_work_order.hard_evidence_decision", "flowguard_work_order.blocker_id"),
            ),
            _contract(
                "packet_result_family.runtime.flowguard_review_handoff",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_ensure_review_packet_for_task_result",
                implements=(
                    "packet_result_family.flowguard_current_report_before_reviewer",
                    "packet_result_family.flowguard_artifact_hard_decision_before_reviewer",
                    "packet_result_family.flowguard_repair_blocker_identity_continuity",
                ),
                external_inputs=("ledger", "subject_packet_id"),
                external_outputs=("review_packet_id",),
                state_reads=("flowguard_work_orders", "flowguard_result"),
                state_writes=("review_packet",),
            ),
            _contract(
                "packet_result_family.runtime.missing_flowguard_review_handoff_blocker",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_record_missing_matching_flowguard_review_handoff_blocker",
                implements=("packet_result_family.review_handoff_blocks_empty_required_flowguard_manifest",),
                external_inputs=("ledger", "subject_packet_id", "target_result_id"),
                external_outputs=("blocker_id",),
                state_reads=("subject_packet", "flowguard_work_orders"),
                state_writes=("active_blockers", "pm_repair_decision_packet"),
            ),
            _contract(
                "packet_result_family.runtime.repair_loop_root_cause_count",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_repair_loop_same_family_rows",
                implements=("packet_result_family.repair_loop_glass_break_root_cause_identity",),
                external_inputs=("ledger", "active_blocker"),
                external_outputs=("same_root_cause_rows",),
                state_reads=("active_blockers.root_cause_loop_key",),
            ),
            _contract(
                "packet_result_family.model.contract_exhaustion_history_matrix",
                path="simulations/flowpilot_contract_exhaustion_mesh_model.py",
                symbol="HISTORICAL_FAILURE_FAMILIES",
                implements=(
                    "packet_result_family.historical_failure_families_have_normal_repair_routes",
                    "packet_result_family.glass_break_is_alarm_not_success_path",
                ),
                external_inputs=("historical_failure_rows", "contract_exhaustion_cells"),
                external_outputs=("historical_failure_repair_routes", "glass_break_alarm_boundary"),
                state_reads=("known_friction_rows", "historical_replay_rows", "hard_gate_rows"),
            ),
            _contract(
                "packet_result_family.runner.contract_exhaustion_test_mesh_owner_consumption",
                path="simulations/run_flowpilot_contract_exhaustion_mesh_checks.py",
                symbol="_test_mesh_report",
                implements=("packet_result_family.contract_exhaustion_matrix_owners_are_child_suites",),
                external_inputs=("required_contract_exhaustion_cells",),
                external_outputs=("required_child_suite_owners", "child_suites", "unregistered_required_child_suites"),
                state_reads=("required_evidence_owner",),
            ),
            _contract(
                "packet_result_family.model.cartesian_control_plane_exhaustion_matrix",
                path="simulations/flowpilot_cartesian_control_plane_exhaustion_model.py",
                symbol="REQUIRED_CARTESIAN_CELLS",
                implements=("packet_result_family.cartesian_control_plane_cells_have_oracles",),
                external_inputs=("control_plane_boundaries", "mutation_alphabet", "handoff_contexts", "downstream_consumers"),
                external_outputs=(
                    "applicable_cartesian_cells",
                    "skipped_cartesian_cells",
                    "repair_oracles",
                    "contract_combination_case_ids",
                    "coverage_shard_ids",
                    "coverage_receipt_ids",
                ),
                state_reads=("contract_exhaustion_bridge_cells", "historical_failure_bridge_cells"),
            ),
            _contract(
                "packet_result_family.runner.cartesian_control_plane_owner_consumption",
                path="simulations/run_flowpilot_cartesian_control_plane_exhaustion_checks.py",
                symbol="_test_mesh_report",
                implements=("packet_result_family.cartesian_control_plane_cells_have_oracles",),
                external_inputs=("required_cartesian_cells", "native_contract_exhaustion_report"),
                external_outputs=(
                    "required_child_suite_owners",
                    "child_suites",
                    "required_coverage_shard_ids",
                    "coverage_receipt_ids",
                    "unregistered_required_child_suites",
                ),
                state_reads=(
                    "required_evidence_owner",
                    "expected_reaction",
                    "normal_repair_context",
                    "coverage_shard_id",
                    "coverage_receipt_id",
                ),
            ),
            _contract(
                "packet_result_family.model.integration_cartesian_coverage_matrix",
                path="simulations/flowpilot_integration_cartesian_coverage_model.py",
                symbol="iter_required_cells",
                implements=("packet_result_family.integration_cartesian_coverage_keeps_pm_optimization_boundary",),
                external_inputs=(
                    "stage_axis",
                    "role_axis",
                    "artifact_family_axis",
                    "failure_class_axis",
                    "severity_axis",
                    "authority_axis",
                    "evidence_timing_axis",
                ),
                external_outputs=(
                    "required_cells",
                    "expected_outcomes",
                    "coverage_shard_ids",
                    "runtime_hard_blocker_boundary",
                    "worker_current_gate_blocker_boundary",
                ),
                state_reads=("pm_system_integration_intent", "reviewer_composition_challenge", "flowguard_route_process_check"),
            ),
            _contract(
                "packet_result_family.runner.integration_cartesian_coverage_checks",
                path="simulations/run_flowpilot_integration_cartesian_coverage_checks.py",
                symbol="run_checks",
                implements=("packet_result_family.integration_cartesian_coverage_keeps_pm_optimization_boundary",),
                external_inputs=("required_cells", "hazard_states"),
                external_outputs=("coverage_report", "hazard_report", "flowguard_report"),
                state_reads=("flowguard_model", "coverage_matrix"),
            ),
            _contract(
                "packet_result_family.runtime.pointer_store_write",
                path="skills/flowpilot/assets/flowpilot_core_runtime/pointer_store.py",
                symbol="write_pointer_json",
                implements=("packet_result_family.pointer_persistence_hardening",),
                external_inputs=("pointer_path", "pointer_payload"),
                external_outputs=("atomic_json_pointer_write",),
                state_writes=(".flowpilot/current.json", ".flowpilot/index.json"),
                side_effects=("router_json_gateway_lock", "atomic_replace", "readback_verify"),
            ),
            _contract(
                "packet_result_family.runtime.pointer_store_recovery",
                path="skills/flowpilot/assets/flowpilot_core_runtime/pointer_store.py",
                symbol="recover_current_pointer",
                implements=("packet_result_family.pointer_persistence_hardening",),
                external_inputs=("project_root",),
                external_outputs=("PointerRecoveryResult",),
                state_reads=(".flowpilot/current.json", ".flowpilot/index.json", ".flowpilot/runs/*/ledger.json"),
                state_writes=(".flowpilot/current.json", ".flowpilot/index.json", "corrupt-backup diagnostics"),
                error_paths=("ambiguous_current_recovery", "pointer_write_in_progress"),
            ),
            _contract(
                "packet_result_family.runtime.submit_result_body_entry",
                path="skills/flowpilot/assets/flowpilot_new_run_commands.py",
                symbol="_resolve_submit_result_body",
                implements=("packet_result_family.submit_result_body_entry_hardening",),
                external_inputs=("--body", "--body-file"),
                external_outputs=("validated_top_level_json_object_body",),
                error_paths=("invalid_json", "json_not_object", "source_conflict", "unreadable_body_file"),
            ),
            _contract(
                "packet_result_family.cli.submit_result_body_file",
                path="skills/flowpilot/assets/flowpilot_new_cli.py",
                symbol="main",
                implements=("packet_result_family.submit_result_body_entry_hardening",),
                external_inputs=("submit-result", "--body", "--body-file"),
                external_outputs=("json_error_or_submission_result",),
            ),
            *_cartesian_risk_shard_contracts(),
        ),
        test_evidence=(
            _evidence(
                "packet_result_family.happy.current_checklist_projection",
                test_name="test_open_packet_submission_checklist_projects_current_handoff_contract",
                path="tests/test_flowpilot_new_entrypoint.py",
                command=(
                    "python -m unittest tests.test_flowpilot_new_entrypoint."
                    "FlowPilotNewEntrypointTests."
                    "test_open_packet_submission_checklist_projects_current_handoff_contract"
                ),
                test_kind=HAPPY,
                covers=("packet_result_family.current_handoff_checklist_single_authority",),
                code_contracts=("packet_result_family.runtime.current_handoff_checklist_projection",),
            ),
            _evidence(
                "packet_result_family.negative.body_authority_rejected",
                test_name="test_open_packet_submission_checklist_rejects_packet_body_as_contract_authority",
                path="tests/test_flowpilot_new_entrypoint.py",
                command=(
                    "python -m unittest tests.test_flowpilot_new_entrypoint."
                    "FlowPilotNewEntrypointTests."
                    "test_open_packet_submission_checklist_rejects_packet_body_as_contract_authority"
                ),
                test_kind=NEGATIVE,
                covers=("packet_result_family.current_handoff_checklist_single_authority",),
                code_contracts=("packet_result_family.runtime.current_handoff_checklist_projection",),
            ),
            _evidence(
                "packet_result_family.happy.strict_fake_ai_open_result",
                test_name="test_real_public_open_packet_result_passes_strict_consumer",
                path="tests/test_flowpilot_contract_driven_fake_ai_open_packet.py",
                command=(
                    "python -m unittest tests.test_flowpilot_contract_driven_fake_ai_open_packet."
                    "FlowPilotContractDrivenFakeAIOpenPacketTests."
                    "test_real_public_open_packet_result_passes_strict_consumer"
                ),
                test_kind=HAPPY,
                covers=("packet_result_family.strict_fake_ai_open_packet_identity",),
                code_contracts=("packet_result_family.fake_ai.from_open_packet_result",),
            ),
            _evidence(
                "packet_result_family.negative.strict_fake_ai_identity_mismatch",
                test_name="test_identity_route_generation_and_projection_mismatches_fail_closed",
                path="tests/test_flowpilot_contract_driven_fake_ai_open_packet.py",
                command=(
                    "python -m unittest tests.test_flowpilot_contract_driven_fake_ai_open_packet."
                    "FlowPilotContractDrivenFakeAIOpenPacketTests."
                    "test_identity_route_generation_and_projection_mismatches_fail_closed"
                ),
                test_kind=NEGATIVE,
                covers=("packet_result_family.strict_fake_ai_open_packet_identity",),
                code_contracts=("packet_result_family.fake_ai.from_open_packet_result",),
            ),
            _evidence(
                "packet_result_family.negative.formal_static_fault_universe",
                test_name="test_static_universe_exhausts_registered_families_and_declared_faults",
                path="tests/test_flowpilot_formal_ai_contract_execution.py",
                command=(
                    "python -m unittest tests.test_flowpilot_formal_ai_contract_execution."
                    "FlowPilotFormalAIContractExecutionTests."
                    "test_static_universe_exhausts_registered_families_and_declared_faults"
                ),
                test_kind=NEGATIVE,
                covers=("packet_result_family.formal_execution_covering_array_receipts",),
                code_contracts=("packet_result_family.formal_ai_execution_closure",),
            ),
            _evidence(
                "packet_result_family.replay.formal_submit_receipts",
                test_name="test_fast_formal_submit_cases_have_real_assertion_receipts",
                path="tests/test_flowpilot_formal_ai_contract_execution.py",
                command=(
                    "python -m unittest tests.test_flowpilot_formal_ai_contract_execution."
                    "FlowPilotFormalAIContractExecutionTests."
                    "test_fast_formal_submit_cases_have_real_assertion_receipts"
                ),
                test_kind=REPLAY,
                covers=("packet_result_family.formal_execution_covering_array_receipts",),
                code_contracts=("packet_result_family.formal_ai_execution_closure",),
            ),
            _evidence(
                "packet_result_family.happy.testmesh_fingerprinted_proof",
                test_name="test_background_evidence_compiler_emits_current_fingerprinted_proofs",
                path="tests/test_flowpilot_acceptance_testmesh.py",
                command=(
                    "python -m unittest tests.test_flowpilot_acceptance_testmesh."
                    "FlowPilotAcceptanceTestMeshTests."
                    "test_background_evidence_compiler_emits_current_fingerprinted_proofs"
                ),
                test_kind=HAPPY,
                covers=("packet_result_family.testmesh_requires_fingerprinted_proof",),
                code_contracts=("packet_result_family.acceptance_testmesh_proof_binding",),
            ),
            _evidence(
                "packet_result_family.negative.testmesh_missing_proof",
                test_name="test_missing_router_background_artifacts_block_broad_routine_gate",
                path="tests/test_flowpilot_acceptance_testmesh.py",
                command=(
                    "python -m unittest tests.test_flowpilot_acceptance_testmesh."
                    "FlowPilotAcceptanceTestMeshTests."
                    "test_missing_router_background_artifacts_block_broad_routine_gate"
                ),
                test_kind=NEGATIVE,
                covers=("packet_result_family.testmesh_requires_fingerprinted_proof",),
                code_contracts=("packet_result_family.acceptance_testmesh_proof_binding",),
            ),
            _evidence(
                "packet_result_family.negative.terminal_pm_repair_blocker",
                test_name="test_fake_end_to_end_terminal_replay_blocker_records_semantic_blocker",
                path="tests/test_flowpilot_new_entrypoint.py",
                command=(
                    "python -m unittest tests.test_flowpilot_new_entrypoint."
                    "FlowPilotNewEntrypointTests."
                    "test_fake_end_to_end_terminal_replay_blocker_records_semantic_blocker"
                ),
                test_kind=NEGATIVE,
                covers=("packet_result_family.dynamic_pm_repair_owner_projection",),
                code_contracts=("packet_result_family.runtime.dynamic_pm_repair_contract",),
            ),
            _evidence(
                "packet_result_family.replay.terminal_pm_repair_converges",
                test_name="test_fake_end_to_end_terminal_replay_blocker_repairs_to_completion",
                path="tests/test_flowpilot_new_entrypoint.py",
                command=(
                    "python -m unittest tests.test_flowpilot_new_entrypoint."
                    "FlowPilotNewEntrypointTests."
                    "test_fake_end_to_end_terminal_replay_blocker_repairs_to_completion"
                ),
                test_kind=REPLAY,
                covers=("packet_result_family.dynamic_pm_repair_owner_projection",),
                code_contracts=("packet_result_family.runtime.dynamic_pm_repair_contract",),
            ),
            _evidence(
                "packet_result_family.happy.stage_matrix_family_coverage",
                test_name="test_stage_evidence_matrix_covers_every_packet_result_family",
                path="tests/test_flowpilot_high_standard_control_flow.py",
                command=(
                    "python -m unittest "
                    "tests.test_flowpilot_high_standard_control_flow."
                    "FlowPilotHighStandardControlFlowTests."
                    "test_stage_evidence_matrix_covers_every_packet_result_family"
                ),
                test_kind=HAPPY,
                covers=("packet_result_family.stage_evidence_matrix_all_families",),
                code_contracts=("packet_result_family.runtime.stage_evidence_matrix",),
            ),
            _evidence(
                "packet_result_family.replay.stage_matrix_all_package_handoffs",
                test_name="test_generated_packet_handoffs_include_stage_matrix_for_each_package_class",
                path="tests/test_flowpilot_high_standard_control_flow.py",
                command=(
                    "python -m unittest "
                    "tests.test_flowpilot_high_standard_control_flow."
                    "FlowPilotHighStandardControlFlowTests."
                    "test_generated_packet_handoffs_include_stage_matrix_for_each_package_class"
                ),
                test_kind=REPLAY,
                covers=("packet_result_family.stage_evidence_matrix_all_families",),
                code_contracts=(
                    "packet_result_family.runtime.current_handoff_stage_matrix",
                    "packet_result_family.runtime.flowguard_stage_matrix",
                    "packet_result_family.runtime.reviewer_stage_matrix",
                ),
            ),
            _evidence(
                "packet_result_family.negative.preplanning_stage_not_final_evidence",
                test_name="test_high_standard_flowguard_packet_uses_preplanning_stage_matrix",
                path="tests/test_flowpilot_high_standard_control_flow.py",
                command=(
                    "python -m unittest "
                    "tests.test_flowpilot_high_standard_control_flow."
                    "FlowPilotHighStandardControlFlowTests."
                    "test_high_standard_flowguard_packet_uses_preplanning_stage_matrix"
                ),
                test_kind=NEGATIVE,
                covers=("packet_result_family.stage_evidence_matrix_all_families",),
                code_contracts=("packet_result_family.runtime.flowguard_stage_matrix",),
            ),
            _evidence(
                "packet_result_family.happy.portable_runtime_self_check_receipt",
                test_name="test_start_run_records_portable_runtime_self_check_receipt",
                path="tests/test_flowpilot_new_entrypoint.py",
                command=(
                    "python -m unittest "
                    "tests.test_flowpilot_new_entrypoint.FlowPilotNewEntrypointTests."
                    "test_start_run_records_portable_runtime_self_check_receipt"
                ),
                test_kind=HAPPY,
                covers=("packet_result_family.portable_runtime_self_check_receipt",),
                code_contracts=("packet_result_family.runtime.record_portable_self_check",),
            ),
            _evidence(
                "packet_result_family.negative.portable_runtime_no_target_dev_script",
                test_name="test_runtime_self_check_does_not_require_target_project_simulations",
                path="tests/test_flowpilot_new_entrypoint.py",
                command=(
                    "python -m unittest "
                    "tests.test_flowpilot_new_entrypoint.FlowPilotNewEntrypointTests."
                    "test_runtime_self_check_does_not_require_target_project_simulations"
                ),
                test_kind=NEGATIVE,
                covers=("packet_result_family.portable_runtime_self_check_receipt",),
                code_contracts=("packet_result_family.runtime.portable_self_check",),
            ),
            _evidence(
                "packet_result_family.happy.research_full",
                test_name="test_research_full_batch_reconciles_from_durable_results_without_manual_event",
                path="tests/router_runtime/packet_result_family.py",
                command="python -m unittest tests.router_runtime.packet_result_family",
                test_kind=HAPPY,
                covers=("packet_result_family.research.durable_event_fold",),
            ),
            _evidence(
                "packet_result_family.edge.research_partial",
                test_name="test_research_partial_batch_waits_only_for_missing_durable_result_member",
                path="tests/router_runtime/packet_result_family.py",
                command="python -m unittest tests.router_runtime.packet_result_family",
                test_kind=EDGE,
                covers=("packet_result_family.research.partial_member_wait",),
            ),
            _evidence(
                "packet_result_family.negative.research_wrong_recipient",
                test_name="test_wrong_recipient_envelope_is_not_counted_as_family_result",
                path="tests/router_runtime/packet_result_family.py",
                command="python -m unittest tests.router_runtime.packet_result_family",
                test_kind=NEGATIVE,
                covers=("packet_result_family.research.recipient_and_sealed_boundary",),
            ),
            _evidence(
                "packet_result_family.happy.current_node_full",
                test_name="test_current_node_full_batch_reconciles_from_durable_results_without_manual_events",
                path="tests/router_runtime/packet_result_family.py",
                command="python -m unittest tests.router_runtime.packet_result_family",
                test_kind=HAPPY,
                covers=("packet_result_family.current_node.durable_event_fold",),
            ),
            _evidence(
                "packet_result_family.edge.current_node_mixed",
                test_name="test_current_node_mixed_manual_and_durable_members_records_remaining_event",
                path="tests/router_runtime/packet_result_family.py",
                command="python -m unittest tests.router_runtime.packet_result_family",
                test_kind=EDGE,
                covers=("packet_result_family.current_node.partial_member_wait",),
            ),
            _evidence(
                "packet_result_family.negative.current_node_wrong_recipient",
                test_name="test_current_node_wrong_recipient_envelope_is_not_counted_as_family_result",
                path="tests/router_runtime/packet_result_family.py",
                command="python -m unittest tests.router_runtime.packet_result_family",
                test_kind=NEGATIVE,
                covers=("packet_result_family.current_node.recipient_and_sealed_boundary",),
            ),
            _evidence(
                "packet_result_family.happy.pm_role_work_full",
                test_name="test_pm_role_work_full_batch_reconciles_from_durable_results_without_manual_events",
                path="tests/router_runtime/packet_result_family.py",
                command="python -m unittest tests.router_runtime.packet_result_family",
                test_kind=HAPPY,
                covers=("packet_result_family.pm_role_work.durable_event_fold",),
            ),
            _evidence(
                "packet_result_family.edge.pm_role_work_partial",
                test_name="test_pm_role_work_partial_batch_waits_only_for_missing_member",
                path="tests/router_runtime/packet_result_family.py",
                command="python -m unittest tests.router_runtime.packet_result_family",
                test_kind=EDGE,
                covers=("packet_result_family.pm_role_work.partial_member_wait",),
            ),
            _evidence(
                "packet_result_family.negative.pm_role_work_wrong_recipient",
                test_name="test_strict_pm_role_work_result_rejects_wrong_next_recipient",
                path="tests/router_runtime/pm_role_work.py",
                command="python -m unittest tests.router_runtime.pm_role_work.PmRoleWorkRuntimeTests.test_strict_pm_role_work_result_rejects_wrong_next_recipient",
                test_kind=NEGATIVE,
                covers=("packet_result_family.pm_role_work.recipient_and_sealed_boundary",),
            ),
            _evidence(
                "packet_result_family.happy.flowguard_consistency_pass",
                test_name="test_review_packet_rejects_generic_decision_summary_result",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_review_packet_rejects_generic_decision_summary_result -q",
                test_kind=HAPPY,
                covers=("packet_result_family.flowguard_current_report_before_reviewer",),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_current_report_gate",
                    "packet_result_family.runtime.flowguard_review_handoff",
                ),
            ),
            _evidence(
                "packet_result_family.negative.flowguard_failed_self_check",
                test_name="test_flowguard_packet_rejects_failed_contract_self_check_without_reviewer",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_flowguard_packet_rejects_failed_contract_self_check_without_reviewer -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.flowguard_current_report_before_reviewer",),
                code_contracts=("packet_result_family.runtime.flowguard_current_report_gate",),
            ),
            _evidence(
                "packet_result_family.negative.flowguard_blocked_child_evidence",
                test_name="test_flowguard_packet_rejects_deleted_evidence_consistency_field_without_reviewer",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_flowguard_packet_rejects_deleted_evidence_consistency_field_without_reviewer -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.flowguard_current_report_before_reviewer",),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_current_report_gate",
                    "packet_result_family.runtime.flowguard_review_handoff",
                ),
            ),
            _evidence(
                "packet_result_family.negative.flowguard_artifact_missing_code_contract",
                test_name="test_flowguard_packet_rejects_artifact_missing_code_contract_without_reviewer",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_flowguard_packet_rejects_artifact_missing_code_contract_without_reviewer -q",
                test_kind=NEGATIVE,
                covers=(
                    "packet_result_family.flowguard_artifact_hard_decision_before_reviewer",
                    "packet_result_family.flowguard_current_report_before_reviewer",
                ),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_current_report_gate",
                    "packet_result_family.runtime.flowguard_artifact_hard_decision",
                    "packet_result_family.runtime.flowguard_work_order_hard_decision",
                    "packet_result_family.runtime.flowguard_review_handoff",
                ),
            ),
            _evidence(
                "packet_result_family.negative.flowguard_missing_evidence_output_policy",
                test_name="test_flowguard_packet_rejects_missing_evidence_output_policy",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_flowguard_packet_rejects_missing_evidence_output_policy -q",
                test_kind=NEGATIVE,
                covers=(
                    "packet_result_family.flowguard_current_report_before_reviewer",
                    "packet_result_family.flowguard_reissue_preserves_current_evidence_policy",
                ),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_current_report_gate",
                    "packet_result_family.runtime.flowguard_reissue_inherited_body_payload",
                ),
            ),
            _evidence(
                "packet_result_family.negative.flowguard_packet_policy_path_authority",
                test_name="test_flowguard_artifact_path_uses_packet_policy_before_derived_run_root",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_flowguard_artifact_path_uses_packet_policy_before_derived_run_root -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.flowguard_artifact_hard_decision_before_reviewer",),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_current_report_gate",
                    "packet_result_family.runtime.flowguard_artifact_hard_decision",
                ),
            ),
            _evidence(
                "packet_result_family.edge.flowguard_reissue_preserves_policy",
                test_name="test_flowguard_fallback_evidence_is_mechanically_reissued",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_flowguard_fallback_evidence_is_mechanically_reissued -q",
                test_kind=EDGE,
                covers=("packet_result_family.flowguard_reissue_preserves_current_evidence_policy",),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_current_report_gate",
                    "packet_result_family.runtime.flowguard_reissue_inherited_body_payload",
                ),
            ),
            _evidence(
                "packet_result_family.edge.flowguard_reissue_preserves_authorized_reads",
                test_name="test_flowguard_reissue_inherits_required_authorized_result_reads",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_flowguard_reissue_inherits_required_authorized_result_reads -q",
                test_kind=EDGE,
                covers=("packet_result_family.flowguard_standard_reissue_preserves_required_authorized_result_reads",),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_reissue_inherited_authorized_reads",
                    "packet_result_family.runtime.flowguard_reissue_issue_task_packet_reads",
                ),
            ),
            _evidence(
                "packet_result_family.edge.flowguard_semantic_recheck_reissue_preserves_authorized_reads",
                test_name="test_flowguard_semantic_recheck_reissue_inherits_required_authorized_reads",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_flowguard_semantic_recheck_reissue_inherits_required_authorized_reads -q",
                test_kind=EDGE,
                covers=(
                    "packet_result_family.flowguard_semantic_recheck_subject_bound",
                    "packet_result_family.flowguard_semantic_recheck_reissue_preserves_required_authorized_result_reads",
                ),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_semantic_recheck_gate",
                    "packet_result_family.runtime.flowguard_reissue_inherited_authorized_reads",
                    "packet_result_family.runtime.flowguard_reissue_issue_task_packet_reads",
                ),
            ),
            _evidence(
                "packet_result_family.negative.flowguard_reissue_requires_inherited_body_open",
                test_name="test_reissued_flowguard_result_blocks_without_inherited_body_open",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_reissued_flowguard_result_blocks_without_inherited_body_open -q",
                test_kind=NEGATIVE,
                covers=(
                    "packet_result_family.flowguard_reissue_preserves_required_authorized_result_reads",
                    "packet_result_family.sealed_body_related_context_reads",
                ),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_reissue_inherited_authorized_reads",
                    "packet_result_family.runtime.flowguard_reissue_issue_task_packet_reads",
                ),
            ),
            _evidence(
                "packet_result_family.negative.empty_required_flowguard_manifest",
                test_name="test_review_packet_is_not_issued_with_empty_required_flowguard_manifest",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_review_packet_is_not_issued_with_empty_required_flowguard_manifest -q",
                test_kind=NEGATIVE,
                covers=(
                    "packet_result_family.review_handoff_blocks_empty_required_flowguard_manifest",
                    "packet_result_family.flowguard_current_report_before_reviewer",
                ),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_review_handoff",
                    "packet_result_family.runtime.missing_flowguard_review_handoff_blocker",
                ),
            ),
            _evidence(
                "packet_result_family.negative.same_root_break_glass",
                test_name="test_break_glass_counts_same_flowguard_root_cause_across_surface_gates",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_break_glass_counts_same_flowguard_root_cause_across_surface_gates -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.repair_loop_glass_break_root_cause_identity",),
                code_contracts=("packet_result_family.runtime.repair_loop_root_cause_count",),
            ),
            _evidence(
                "packet_result_family.edge.flowguard_auto_recheck_inherits_blocker",
                test_name="test_repair_task_flowguard_packet_inherits_blocker_identity",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_repair_task_flowguard_packet_inherits_blocker_identity -q",
                test_kind=EDGE,
                covers=("packet_result_family.flowguard_repair_blocker_identity_continuity",),
                code_contracts=("packet_result_family.runtime.flowguard_packet_issue_inherits_blocker",),
            ),
            _evidence(
                "packet_result_family.edge.flowguard_explicit_recheck_inherits_blocker",
                test_name="test_explicit_flowguard_action_inherits_repair_blocker_identity",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_explicit_flowguard_action_inherits_repair_blocker_identity -q",
                test_kind=HAPPY,
                covers=("packet_result_family.flowguard_repair_blocker_identity_continuity",),
                code_contracts=("packet_result_family.runtime.flowguard_packet_issue_inherits_blocker",),
            ),
            _evidence(
                "packet_result_family.negative.repair_identity_mismatch_blocks",
                test_name="test_formal_repair_identity_mismatch_is_runtime_mechanical_blocker",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_formal_repair_identity_mismatch_is_runtime_mechanical_blocker -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.flowguard_repair_blocker_identity_continuity",),
                code_contracts=("packet_result_family.runtime.repair_blocker_identity_formal_gate",),
            ),
            _evidence(
                "packet_result_family.negative.flowguard_shape_only_semantic_recheck",
                test_name="test_semantic_recheck_rejects_shape_only_flowguard_pass",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_semantic_recheck_rejects_shape_only_flowguard_pass -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.flowguard_semantic_recheck_subject_bound",),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_current_report_gate",
                    "packet_result_family.runtime.flowguard_semantic_recheck_gate",
                ),
            ),
            _evidence(
                "packet_result_family.happy.flowguard_subject_bound_semantic_recheck",
                test_name="test_semantic_recheck_subject_bound_flowguard_pass_reaches_reviewer",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_semantic_recheck_subject_bound_flowguard_pass_reaches_reviewer -q",
                test_kind=HAPPY,
                covers=(
                    "packet_result_family.flowguard_semantic_recheck_subject_bound",
                    "packet_result_family.flowguard_artifact_hard_decision_before_reviewer",
                    "packet_result_family.flowguard_repair_blocker_identity_continuity",
                ),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_current_report_gate",
                    "packet_result_family.runtime.flowguard_artifact_hard_decision",
                    "packet_result_family.runtime.flowguard_work_order_hard_decision",
                    "packet_result_family.runtime.flowguard_review_handoff",
                ),
            ),
            _evidence(
                "packet_result_family.happy.flowguard_ai_contract_projection",
                test_name="test_semantic_recheck_contract_projects_ai_facing_fields_and_options",
                path="tests/test_flowpilot_ai_contract_projection.py",
                command=(
                    "python -m unittest tests.test_flowpilot_ai_contract_projection."
                    "FlowPilotAIContractProjectionTests."
                    "test_semantic_recheck_contract_projects_ai_facing_fields_and_options"
                ),
                test_kind=HAPPY,
                covers=("packet_result_family.flowguard_semantic_recheck_ai_facing_projection",),
                code_contracts=(
                    "packet_result_family.runtime.effective_result_contract_profiles",
                    "packet_result_family.runtime.current_handoff_result_profile_contract",
                ),
            ),
            _evidence(
                "packet_result_family.negative.flowguard_ai_contract_forbidden_alias_feedback",
                test_name="test_semantic_recheck_near_synonyms_reissue_with_correct_minimal_shape",
                path="tests/test_flowpilot_ai_contract_projection.py",
                command=(
                    "python -m unittest tests.test_flowpilot_ai_contract_projection."
                    "FlowPilotAIContractProjectionTests."
                    "test_semantic_recheck_near_synonyms_reissue_with_correct_minimal_shape"
                ),
                test_kind=NEGATIVE,
                covers=(
                    "packet_result_family.flowguard_semantic_recheck_ai_facing_projection",
                    "packet_result_family.flowguard_semantic_recheck_corrected_retry_convergence",
                ),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_semantic_recheck_gate",
                    "packet_result_family.runtime.current_contract_reissue_feedback",
                ),
            ),
            _evidence(
                "packet_result_family.negative.flowguard_semantic_recheck_purpose_string",
                test_name="test_semantic_recheck_purpose_string_is_rejected_as_consumed_result_id",
                path="tests/test_flowpilot_ai_contract_projection.py",
                command=(
                    "python -m unittest tests.test_flowpilot_ai_contract_projection."
                    "FlowPilotAIContractProjectionTests."
                    "test_semantic_recheck_purpose_string_is_rejected_as_consumed_result_id"
                ),
                test_kind=NEGATIVE,
                covers=(
                    "packet_result_family.flowguard_semantic_recheck_subject_bound",
                    "packet_result_family.flowguard_semantic_recheck_ai_facing_projection",
                ),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_semantic_recheck_gate",
                    "packet_result_family.runtime.current_contract_reissue_feedback",
                ),
            ),
            _evidence(
                "packet_result_family.replay.flowguard_ai_contract_corrected_retry",
                test_name="test_semantic_recheck_wrong_value_then_corrected_retry_returns_to_legal_path",
                path="tests/test_flowpilot_ai_contract_projection.py",
                command=(
                    "python -m unittest tests.test_flowpilot_ai_contract_projection."
                    "FlowPilotAIContractProjectionTests."
                    "test_semantic_recheck_wrong_value_then_corrected_retry_returns_to_legal_path"
                ),
                test_kind=REPLAY,
                covers=("packet_result_family.flowguard_semantic_recheck_corrected_retry_convergence",),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_semantic_recheck_gate",
                    "packet_result_family.runtime.current_contract_reissue_feedback",
                ),
            ),
            _evidence(
                "packet_result_family.negative.contract_driven_fake_ai_missing_options",
                test_name="test_contract_driven_fake_ai_refuses_to_guess_when_finite_options_are_missing",
                path="tests/test_flowpilot_ai_contract_projection.py",
                command=(
                    "python -m unittest tests.test_flowpilot_ai_contract_projection."
                    "FlowPilotAIContractProjectionTests."
                    "test_contract_driven_fake_ai_refuses_to_guess_when_finite_options_are_missing"
                ),
                test_kind=NEGATIVE,
                covers=(
                    "packet_result_family.flowguard_semantic_recheck_ai_facing_projection",
                    "packet_result_family.contract_driven_fake_ai_cartesian_retry",
                ),
                code_contracts=("packet_result_family.simulation.contract_driven_fake_ai_responder",),
            ),
            _evidence(
                "packet_result_family.replay.contract_driven_fake_ai_cartesian_retry",
                test_name="test_contract_driven_fake_ai_wrong_value_rows_repair_each_finite_option",
                path="tests/test_flowpilot_ai_contract_projection.py",
                command=(
                    "python -m unittest tests.test_flowpilot_ai_contract_projection."
                    "FlowPilotAIContractProjectionTests."
                    "test_contract_driven_fake_ai_wrong_value_rows_repair_each_finite_option"
                ),
                test_kind=REPLAY,
                covers=(
                    "packet_result_family.flowguard_semantic_recheck_ai_facing_projection",
                    "packet_result_family.flowguard_semantic_recheck_corrected_retry_convergence",
                    "packet_result_family.contract_driven_fake_ai_cartesian_retry",
                ),
                code_contracts=(
                    "packet_result_family.simulation.contract_driven_fake_ai_responder",
                    "packet_result_family.runtime.current_contract_reissue_feedback",
                ),
            ),
            _evidence(
                "packet_result_family.replay.fake_ai_runtime_replay_matrix",
                test_name="test_runtime_replay_cells_bind_fake_ai_errors_to_runtime_reactions",
                path="tests/test_flowpilot_fake_ai_runtime_replay.py",
                command=(
                    "python -m unittest tests.test_flowpilot_fake_ai_runtime_replay."
                    "FlowPilotFakeAIRuntimeReplayTests."
                    "test_runtime_replay_cells_bind_fake_ai_errors_to_runtime_reactions"
                ),
                test_kind=REPLAY,
                covers=("packet_result_family.fake_ai_runtime_replay_matrix_closure",),
                code_contracts=(
                    "packet_result_family.model.fake_ai_runtime_replay_matrix",
                    "packet_result_family.runner.fake_ai_runtime_replay_checks",
                    "packet_result_family.simulation.contract_driven_fake_ai_responder",
                ),
            ),
            _evidence(
                "packet_result_family.replay.control_plane_ledger_hygiene_cartesian_matrix",
                test_name="test_control_plane_ledger_hygiene_fake_ai_matrix_is_cartesian",
                path="tests/test_flowpilot_fake_ai_runtime_replay.py",
                command=(
                    "python -m unittest tests.test_flowpilot_fake_ai_runtime_replay."
                    "FlowPilotFakeAIRuntimeReplayTests."
                    "test_control_plane_ledger_hygiene_fake_ai_matrix_is_cartesian"
                ),
                test_kind=REPLAY,
                covers=("packet_result_family.control_plane_ledger_hygiene_cartesian_matrix",),
                code_contracts=(
                    "packet_result_family.model.fake_ai_runtime_replay_matrix",
                    "packet_result_family.runner.fake_ai_runtime_replay_checks",
                ),
            ),
            _evidence(
                "packet_result_family.negative.control_plane_ledger_hygiene_coverage_matrix",
                test_name="test_control_plane_ledger_hygiene_cells_have_runtime_owners",
                path="tests/test_flowpilot_synthetic_agent_coverage_matrix.py",
                command=(
                    "python -m unittest tests.test_flowpilot_synthetic_agent_coverage_matrix."
                    "FlowPilotSyntheticAgentCoverageMatrixTests."
                    "test_control_plane_ledger_hygiene_cells_have_runtime_owners"
                ),
                test_kind=NEGATIVE,
                covers=("packet_result_family.control_plane_ledger_hygiene_cartesian_matrix",),
                code_contracts=("packet_result_family.model.fake_ai_runtime_replay_matrix",),
            ),
            _evidence(
                "packet_result_family.negative.fake_ai_runtime_replay_hazards",
                test_name="test_fake_ai_runtime_replay_runner_accepts_valid_and_rejects_hazards",
                path="tests/test_flowpilot_fake_ai_runtime_replay.py",
                command=(
                    "python -m unittest tests.test_flowpilot_fake_ai_runtime_replay."
                    "FlowPilotFakeAIRuntimeReplayTests."
                    "test_fake_ai_runtime_replay_runner_accepts_valid_and_rejects_hazards"
                ),
                test_kind=NEGATIVE,
                covers=("packet_result_family.fake_ai_runtime_replay_matrix_closure",),
                code_contracts=(
                    "packet_result_family.model.fake_ai_runtime_replay_matrix",
                    "packet_result_family.runner.fake_ai_runtime_replay_checks",
                ),
            ),
            _evidence(
                "packet_result_family.replay.real_issue_backfeed_registry",
                test_name="test_real_issue_backfeed_registry_bridges_every_issue_to_runtime_replay",
                path="tests/test_flowpilot_real_issue_backfeed.py",
                command=(
                    "python -m unittest tests.test_flowpilot_real_issue_backfeed."
                    "FlowPilotRealIssueBackfeedTests."
                    "test_real_issue_backfeed_registry_bridges_every_issue_to_runtime_replay"
                ),
                test_kind=REPLAY,
                covers=("packet_result_family.real_issue_backfeed_registry_bridge",),
                code_contracts=("packet_result_family.model.real_issue_backfeed_registry",),
            ),
            _evidence(
                "packet_result_family.negative.real_issue_backfeed_rejects_incomplete_rows",
                test_name="test_real_issue_backfeed_rejects_missing_fields_and_sealed_body_copies",
                path="tests/test_flowpilot_real_issue_backfeed.py",
                command=(
                    "python -m unittest tests.test_flowpilot_real_issue_backfeed."
                    "FlowPilotRealIssueBackfeedTests."
                    "test_real_issue_backfeed_rejects_missing_fields_and_sealed_body_copies"
                ),
                test_kind=NEGATIVE,
                covers=("packet_result_family.real_issue_backfeed_registry_bridge",),
                code_contracts=("packet_result_family.model.real_issue_backfeed_registry",),
            ),
            _evidence(
                "packet_result_family.happy.related_blocker_bodies_delivered_to_pm",
                test_name="test_reviewer_required_repair_reaches_pm_repair_packet",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_reviewer_required_repair_reaches_pm_repair_packet -q",
                test_kind=HAPPY,
                covers=("packet_result_family.sealed_body_related_context_reads",),
                code_contracts=("packet_result_family.runtime.blocker_related_authorized_reads",),
            ),
            _evidence(
                "packet_result_family.negative.related_blocker_bodies_must_be_opened",
                test_name="test_pm_repair_decision_blocks_without_opening_all_related_bodies",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_pm_repair_decision_blocks_without_opening_all_related_bodies -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.sealed_body_related_context_reads",),
                code_contracts=("packet_result_family.runtime.blocker_related_authorized_reads",),
            ),
            _evidence(
                "packet_result_family.happy.pm_repair_obligations_projected",
                test_name="test_pm_repair_packet_projects_blocker_body_into_repair_obligations",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_pm_repair_packet_projects_blocker_body_into_repair_obligations -q",
                test_kind=HAPPY,
                covers=(
                    "packet_result_family.sealed_body_related_context_reads",
                    "packet_result_family.pm_repair_evidence_obligation_lifecycle",
                ),
                code_contracts=(
                    "packet_result_family.runtime.blocker_related_authorized_reads",
                    "packet_result_family.runtime.pm_repair_obligation_disposition_gate",
                ),
            ),
            _evidence(
                "packet_result_family.negative.pm_repair_reason_only_obligation_loss",
                test_name="test_pm_repair_decision_reason_only_is_rejected_when_obligations_exist",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_pm_repair_decision_reason_only_is_rejected_when_obligations_exist -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.pm_repair_evidence_obligation_lifecycle",),
                code_contracts=("packet_result_family.runtime.pm_repair_obligation_disposition_gate",),
            ),
            _evidence(
                "packet_result_family.negative.pm_repair_stale_or_registry_only_obligation",
                test_name="test_pm_repair_obligation_rejects_stale_or_registry_only_disposition",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_pm_repair_obligation_rejects_stale_or_registry_only_disposition -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.pm_repair_evidence_obligation_lifecycle",),
                code_contracts=("packet_result_family.runtime.pm_repair_obligation_disposition_gate",),
            ),
            _evidence(
                "packet_result_family.negative.flowguard_missing_repair_obligation_consumption",
                test_name="test_repair_packet_and_flowguard_recheck_must_consume_repair_obligations",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_repair_packet_and_flowguard_recheck_must_consume_repair_obligations -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.pm_repair_evidence_obligation_lifecycle",),
                code_contracts=(
                    "packet_result_family.runtime.repair_obligation_context_projection",
                    "packet_result_family.runtime.flowguard_semantic_recheck_gate",
                ),
            ),
            _evidence(
                "packet_result_family.replay.flowguard_consistent_block",
                test_name="test_flowguard_packet_block_with_compact_blocker_does_not_issue_reviewer",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_flowguard_packet_block_with_compact_blocker_does_not_issue_reviewer -q",
                test_kind=REPLAY,
                covers=("packet_result_family.flowguard_current_report_before_reviewer",),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_current_report_gate",
                    "packet_result_family.runtime.flowguard_review_handoff",
                ),
            ),
            _evidence(
                "packet_result_family.replay.fake_e2e_flowguard_consistency_chaos",
                test_name="test_fake_end_to_end_flowguard_consistency_chaos_reissues_and_finishes",
                path="tests/test_flowpilot_new_entrypoint.py",
                command="python -m pytest tests/test_flowpilot_new_entrypoint.py -k test_fake_end_to_end_flowguard_consistency_chaos_reissues_and_finishes -q",
                test_kind=REPLAY,
                covers=("packet_result_family.flowguard_current_report_before_reviewer",),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_current_report_gate",
                    "packet_result_family.runtime.flowguard_review_handoff",
                ),
            ),
            _evidence(
                "packet_result_family.replay.fake_e2e_flowguard_artifact_chaos",
                test_name="test_fake_end_to_end_flowguard_artifact_chaos_reissues_and_finishes",
                path="tests/test_flowpilot_new_entrypoint.py",
                command="python -m pytest tests/test_flowpilot_new_entrypoint.py -k test_fake_end_to_end_flowguard_artifact_chaos_reissues_and_finishes -q",
                test_kind=REPLAY,
                covers=(
                    "packet_result_family.flowguard_artifact_hard_decision_before_reviewer",
                    "packet_result_family.flowguard_current_report_before_reviewer",
                ),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_current_report_gate",
                    "packet_result_family.runtime.flowguard_artifact_hard_decision",
                    "packet_result_family.runtime.flowguard_review_handoff",
                ),
            ),
            _evidence(
                "packet_result_family.replay.fake_e2e_shallow_flowguard_reviewer_block",
                test_name="test_fake_end_to_end_shallow_flowguard_is_reviewer_blocked",
                path="tests/test_flowpilot_new_entrypoint.py",
                command="python -m pytest tests/test_flowpilot_new_entrypoint.py -k test_fake_end_to_end_shallow_flowguard_is_reviewer_blocked -q",
                test_kind=REPLAY,
                covers=(
                    "packet_result_family.reviewer_blocks_shallow_flowguard_depth",
                    "packet_result_family.sealed_body_related_context_reads",
                ),
                code_contracts=(
                    "packet_result_family.runtime.review_packet_flowguard_depth_instruction",
                    "packet_result_family.simulation.fake_e2e_shallow_flowguard_reviewer_block",
                ),
            ),
            _evidence(
                "packet_result_family.prompt.reviewer_shallow_flowguard_depth_card",
                test_name="test_reviewer_card_blocks_shallow_flowguard_with_pm_recheck_guidance",
                path="tests/test_flowpilot_card_instruction_coverage.py",
                command="python -m pytest tests/test_flowpilot_card_instruction_coverage.py -k test_reviewer_card_blocks_shallow_flowguard_with_pm_recheck_guidance -q",
                test_kind=REPLAY,
                covers=("packet_result_family.reviewer_blocks_shallow_flowguard_depth",),
                code_contracts=("packet_result_family.prompt.reviewer_shallow_flowguard_depth_card",),
            ),
            _evidence(
                "packet_result_family.negative.shallow_flowguard_reviewer_block",
                test_name="test_fake_end_to_end_shallow_flowguard_is_reviewer_blocked",
                path="tests/test_flowpilot_new_entrypoint.py",
                command="python -m pytest tests/test_flowpilot_new_entrypoint.py -k test_fake_end_to_end_shallow_flowguard_is_reviewer_blocked -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.reviewer_blocks_shallow_flowguard_depth",),
                code_contracts=(
                    "packet_result_family.runtime.review_packet_flowguard_depth_instruction",
                    "packet_result_family.simulation.fake_e2e_shallow_flowguard_reviewer_block",
                ),
            ),
            _evidence(
                "packet_result_family.replay.fake_e2e_authorized_material_openings",
                test_name="test_fake_end_to_end_rehearsal_reaches_final_closure",
                path="tests/test_flowpilot_new_entrypoint.py",
                command="python -m pytest tests/test_flowpilot_new_entrypoint.py -k test_fake_end_to_end_rehearsal_reaches_final_closure -q",
                test_kind=REPLAY,
                covers=(
                    "packet_result_family.clean_e2e_authorized_material_openings",
                    "packet_result_family.sealed_body_related_context_reads",
                    "packet_result_family.flowguard_current_report_before_reviewer",
                ),
                code_contracts=(
                    "packet_result_family.simulation.fake_e2e_authorized_material_proof",
                    "packet_result_family.runtime.flowguard_current_report_gate",
                    "packet_result_family.runtime.flowguard_review_handoff",
                ),
            ),
            _evidence(
                "packet_result_family.replay.historical_skillguard_flowguard_artifact_block",
                test_name="test_historical_skillguard_flowguard_artifact_block_is_not_authoritative",
                path="tests/test_flowpilot_historical_live_run_replay.py",
                command="python -m pytest tests/test_flowpilot_historical_live_run_replay.py -k test_historical_skillguard_flowguard_artifact_block_is_not_authoritative -q",
                test_kind=REPLAY,
                covers=(
                    "packet_result_family.flowguard_artifact_hard_decision_before_reviewer",
                    "packet_result_family.flowguard_current_report_before_reviewer",
                ),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_current_report_gate",
                    "packet_result_family.runtime.flowguard_artifact_hard_decision",
                    "packet_result_family.runtime.flowguard_review_handoff",
                ),
            ),
            _evidence(
                "packet_result_family.replay.contract_exhaustion_mesh",
                test_name="test_contract_exhaustion_mesh_accepts_valid_and_rejects_hazards",
                path="tests/test_flowpilot_contract_exhaustion_mesh.py",
                command="python -m pytest tests/test_flowpilot_contract_exhaustion_mesh.py -q",
                test_kind=REPLAY,
                covers=(
                    "packet_result_family.flowguard_reissue_preserves_current_evidence_policy",
                    "packet_result_family.flowguard_reissue_preserves_required_authorized_result_reads",
                    "packet_result_family.review_handoff_blocks_empty_required_flowguard_manifest",
                    "packet_result_family.repair_loop_glass_break_root_cause_identity",
                    "packet_result_family.glass_break_is_alarm_not_success_path",
                ),
                code_contracts=(
                    "packet_result_family.runtime.flowguard_reissue_inherited_body_payload",
                    "packet_result_family.runtime.flowguard_reissue_inherited_authorized_reads",
                    "packet_result_family.runtime.flowguard_reissue_issue_task_packet_reads",
                    "packet_result_family.runtime.missing_flowguard_review_handoff_blocker",
                    "packet_result_family.runtime.repair_loop_root_cause_count",
                    "packet_result_family.model.contract_exhaustion_history_matrix",
                ),
            ),
            _evidence(
                "packet_result_family.replay.contract_exhaustion_historical_failure_families",
                test_name="test_historical_failure_families_require_normal_repair_before_glass_break",
                path="tests/test_flowpilot_contract_exhaustion_mesh.py",
                command="python -m pytest tests/test_flowpilot_contract_exhaustion_mesh.py -q",
                test_kind=REPLAY,
                covers=(
                    "packet_result_family.historical_failure_families_have_normal_repair_routes",
                    "packet_result_family.glass_break_is_alarm_not_success_path",
                ),
                code_contracts=(
                    "packet_result_family.model.contract_exhaustion_history_matrix",
                ),
            ),
            _evidence(
                "packet_result_family.replay.contract_exhaustion_test_mesh_owner_consumption",
                test_name="test_contract_exhaustion_test_mesh_registers_every_required_owner",
                path="tests/test_flowpilot_contract_exhaustion_mesh.py",
                command="python -m pytest tests/test_flowpilot_contract_exhaustion_mesh.py -q",
                test_kind=REPLAY,
                covers=("packet_result_family.contract_exhaustion_matrix_owners_are_child_suites",),
                code_contracts=(
                    "packet_result_family.runner.contract_exhaustion_test_mesh_owner_consumption",
                ),
            ),
            _evidence(
                "packet_result_family.negative.glass_break_alarm_not_success_path",
                test_name="test_contract_exhaustion_mesh_accepts_valid_and_rejects_hazards",
                path="tests/test_flowpilot_contract_exhaustion_mesh.py",
                command="python -m pytest tests/test_flowpilot_contract_exhaustion_mesh.py -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.glass_break_is_alarm_not_success_path",),
                code_contracts=(
                    "packet_result_family.model.contract_exhaustion_history_matrix",
                    "packet_result_family.runtime.repair_loop_root_cause_count",
                ),
            ),
            _evidence(
                "packet_result_family.replay.cartesian_control_plane_exhaustion",
                test_name="test_cartesian_runner_accepts_valid_and_rejects_hazards",
                path="tests/test_flowpilot_cartesian_control_plane_exhaustion.py",
                command="python -m pytest tests/test_flowpilot_cartesian_control_plane_exhaustion.py -q",
                test_kind=REPLAY,
                covers=("packet_result_family.cartesian_control_plane_cells_have_oracles",),
                code_contracts=(
                    "packet_result_family.model.cartesian_control_plane_exhaustion_matrix",
                    "packet_result_family.runner.cartesian_control_plane_owner_consumption",
                ),
            ),
            _evidence(
                "packet_result_family.negative.cartesian_normal_repair_not_glassbreak",
                test_name="test_normal_repair_cells_never_expect_glassbreak",
                path="tests/test_flowpilot_cartesian_control_plane_exhaustion.py",
                command="python -m pytest tests/test_flowpilot_cartesian_control_plane_exhaustion.py -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.cartesian_control_plane_cells_have_oracles",),
                code_contracts=(
                    "packet_result_family.model.cartesian_control_plane_exhaustion_matrix",
                    "packet_result_family.runner.cartesian_control_plane_owner_consumption",
                ),
            ),
            _evidence(
                "packet_result_family.replay.integration_cartesian_full_matrix",
                test_name="test_integration_cartesian_runner_accepts_full_matrix",
                path="tests/test_flowpilot_integration_cartesian_coverage.py",
                command="python -m pytest tests/test_flowpilot_integration_cartesian_coverage.py -q",
                test_kind=REPLAY,
                covers=("packet_result_family.integration_cartesian_coverage_keeps_pm_optimization_boundary",),
                code_contracts=(
                    "packet_result_family.model.integration_cartesian_coverage_matrix",
                    "packet_result_family.runner.integration_cartesian_coverage_checks",
                ),
            ),
            _evidence(
                "packet_result_family.negative.integration_cartesian_authority_boundary",
                test_name="test_worker_and_runtime_do_not_gain_semantic_integration_authority",
                path="tests/test_flowpilot_integration_cartesian_coverage.py",
                command="python -m pytest tests/test_flowpilot_integration_cartesian_coverage.py -q",
                test_kind=NEGATIVE,
                covers=("packet_result_family.integration_cartesian_coverage_keeps_pm_optimization_boundary",),
                code_contracts=(
                    "packet_result_family.model.integration_cartesian_coverage_matrix",
                    "packet_result_family.runner.integration_cartesian_coverage_checks",
                ),
            ),
            _evidence(
                "packet_result_family.edge.pointer_current_recovery",
                test_name="test_corrupt_current_pointer_recovers_from_single_current_run_evidence",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_corrupt_current_pointer_recovers_from_single_current_run_evidence",
                test_kind=EDGE,
                covers=("packet_result_family.pointer_persistence_hardening",),
                code_contracts=(
                    "packet_result_family.runtime.pointer_store_write",
                    "packet_result_family.runtime.pointer_store_recovery",
                ),
            ),
            _evidence(
                "packet_result_family.negative.pointer_ambiguous_or_locked_recovery",
                test_name="test_corrupt_current_pointer_does_not_guess_between_multiple_runs",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_corrupt_current_pointer_does_not_guess_between_multiple_runs",
                test_kind=NEGATIVE,
                covers=("packet_result_family.pointer_persistence_hardening",),
                code_contracts=("packet_result_family.runtime.pointer_store_recovery",),
            ),
            _evidence(
                "packet_result_family.edge.submit_result_body_file",
                test_name="test_submit_result_body_file_accepts_top_level_json_object",
                path="tests/test_flowpilot_new_entrypoint.py",
                command="python -m unittest tests.test_flowpilot_new_entrypoint.FlowPilotNewEntrypointTests.test_submit_result_body_file_accepts_top_level_json_object",
                test_kind=EDGE,
                covers=("packet_result_family.submit_result_body_entry_hardening",),
                code_contracts=(
                    "packet_result_family.runtime.submit_result_body_entry",
                    "packet_result_family.cli.submit_result_body_file",
                ),
            ),
            _evidence(
                "packet_result_family.negative.submit_result_pseudo_json",
                test_name="test_submit_result_rejects_pseudo_json_before_loading_current_run",
                path="tests/test_flowpilot_new_entrypoint.py",
                command="python -m unittest tests.test_flowpilot_new_entrypoint.FlowPilotNewEntrypointTests.test_submit_result_rejects_pseudo_json_before_loading_current_run",
                test_kind=NEGATIVE,
                covers=("packet_result_family.submit_result_body_entry_hardening",),
                code_contracts=("packet_result_family.runtime.submit_result_body_entry",),
            ),
            *_cartesian_risk_shard_evidence(),
        ),
    )


    route_mutation = ModelTestAlignmentPlan(
        model_id="route_mutation",
        obligations=(
            _obligation(
                "route_mutation.topology_and_recheck",
                obligation_type="contract",
                description="Route mutation declares topology, affected nodes, process/product rechecks, and old packet supersession before activation.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "route_mutation.sibling_replacement_stales_old_evidence",
                obligation_type="hazard",
                description="Sibling branch replacement marks old sibling evidence stale and projects replacement/replay scope in the route display.",
                required_test_kinds=(NEGATIVE, EDGE),
            ),
            _obligation(
                "route_mutation.stale_prior_route_repair_blocker_supersession",
                obligation_type="hazard",
                description="Route mutation supersedes older-route repair-open blockers while preserving current-version and unproven-version repair blockers.",
                required_test_kinds=(NEGATIVE, EDGE),
                allow_shared_implementation=True,
            ),
        ),
        code_contracts=(
            _contract(
                "route_mutation.runtime.repair_open_blocker_supersession",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_supersede_repair_open_blockers_for_route_mutation",
                implements=("route_mutation.stale_prior_route_repair_blocker_supersession",),
                external_inputs=("ledger", "affected_packets", "mutation_id", "new_route_version"),
                state_reads=("active_blockers", "packets", "route_nodes", "active_route_version"),
                state_writes=("active_blockers", "packets"),
                side_effects=("semantic_blocker_superseded_by_route_mutation",),
            ),
        ),
        test_evidence=(
            _evidence(
                "route_mutation.happy.contract_fixture",
                test_name="TestRouteMutationChildContractFixture",
                path="tests/flowpilot_route_mutation_contracts.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_route_mutation",
                test_kind=HAPPY,
                covers=("route_mutation.topology_and_recheck",),
            ),
            _evidence(
                "route_mutation.negative.required_preconditions",
                test_name="test_route_mutation_and_final_ledger_have_required_preconditions",
                path="tests/router_runtime/route_mutation_preconditions.py",
                command="python -m unittest tests.router_runtime.route_mutation_preconditions.RouteMutationPreconditionRuntimeTests.test_route_mutation_and_final_ledger_have_required_preconditions",
                test_kind=NEGATIVE,
                covers=("route_mutation.topology_and_recheck",),
            ),
            _evidence(
                "route_mutation.edge.sibling_replacement_display",
                test_name="test_sibling_branch_replacement_draws_replacement_and_replay_scope",
                path="tests/test_flowpilot_user_flow_diagram.py",
                command="python -m unittest tests.test_flowpilot_user_flow_diagram.FlowPilotUserFlowDiagramTests.test_sibling_branch_replacement_draws_replacement_and_replay_scope",
                test_kind=EDGE,
                covers=("route_mutation.sibling_replacement_stales_old_evidence",),
            ),
            _evidence(
                "route_mutation.negative.old_sibling_proof",
                test_name="test_route_mutation_sibling_branch_replacement_blocks_old_sibling_proof",
                path="tests/router_runtime/route_mutation_sibling_replacement.py",
                command="python -m unittest tests.router_runtime.route_mutation_sibling_replacement.RouteMutationSiblingReplacementRuntimeTests.test_route_mutation_sibling_branch_replacement_blocks_old_sibling_proof",
                test_kind=NEGATIVE,
                covers=("route_mutation.sibling_replacement_stales_old_evidence",),
            ),
            _evidence(
                "route_mutation.negative.stale_prior_route_repair_blocker",
                test_name="test_route_mutation_supersedes_prior_route_repair_open_blockers",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_route_mutation_supersedes_prior_route_repair_open_blockers",
                test_kind=NEGATIVE,
                covers=("route_mutation.stale_prior_route_repair_blocker_supersession",),
                code_contracts=("route_mutation.runtime.repair_open_blocker_supersession",),
            ),
            _evidence(
                "route_mutation.edge.current_or_unproven_repair_blocker_preserved",
                test_name="test_route_mutation_preserves_current_unproven_and_dispositioned_repair_open_blockers",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_route_mutation_preserves_current_unproven_and_dispositioned_repair_open_blockers",
                test_kind=EDGE,
                covers=("route_mutation.stale_prior_route_repair_blocker_supersession",),
                code_contracts=("route_mutation.runtime.repair_open_blocker_supersession",),
            ),
        ),
    )

    unified_repair_integrity = ModelTestAlignmentPlan(
        model_id="flowpilot_unified_repair_integrity",
        obligations=(
            _obligation(
                "unified_repair.pm_historical_direct_entry_no_blocker",
                obligation_type="transition",
                description=(
                    "A PM-discovered historical-node defect enters the ordinary repair decision engine from a "
                    "structured defect observation and impact frontier without manufacturing a semantic blocker."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "unified_repair.same_slot_replacement_single_authority",
                obligation_type="invariant",
                description=(
                    "The repair graft preserves logical parent, business intent, and logical slot; the historical "
                    "node remains immutable and exactly one replacement is active authority."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "unified_repair.repair_child_under_active_replacement",
                obligation_type="invariant",
                description=(
                    "A bounded repair child is attached only beneath the active replacement node, enters the active "
                    "route/node order, final ledger, and terminal target set, receives its own Worker packet/result "
                    "and acceptance, and is consumed by parent closure; it never hangs beneath the superseded node."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "unified_repair.worker_flowguard_reviewer_chain",
                obligation_type="transition",
                description=(
                    "Substantive repair executes through a fresh Worker packet/result, then current FlowGuard "
                    "evidence, then an independent Reviewer result for that same repair generation."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "unified_repair.contract_evidence_generation",
                obligation_type="hazard",
                description=(
                    "Repair contract, Worker result, FlowGuard evidence, Reviewer evidence, PM acceptance, and closure "
                    "all bind the current repair generation; pre-contract or prior-generation evidence is rejected."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_implementation=True,
            ),
            _obligation(
                "unified_repair.decision_gate_before_effect_commit",
                obligation_type="transition",
                description=(
                    "A continue-repair decision stages its effect, then completes FlowGuard, PM absorption, the "
                    "pre-effect Reviewer gate, and system validation before _apply_staged_pm_decision_gate commits "
                    "the effect and opens Worker work. The later Worker-result Reviewer is a distinct gate. Rejected "
                    "or cancelled gates cannot commit, open Worker, retain an orphan effect, or consume a terminal round."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "unified_repair.unaffected_sibling_rebind_conservation",
                obligation_type="invariant",
                description=(
                    "Replacing one target conserves the effective active-member set: every unaffected sibling is "
                    "rebound into the new route version and remains visible to progress and final-ledger projections."
                ),
                required_test_kinds=(EDGE, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "unified_repair.affected_downstream_replay",
                obligation_type="transition",
                description=(
                    "Every dependency-affected downstream node and parent replay is invalidated and freshly replayed "
                    "before closure, including a same-slot repair whenever its impact frontier reaches a parent or "
                    "downstream consumer, while unaffected siblings retain valid evidence."
                ),
                required_test_kinds=(REPLAY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "unified_repair.repeated_lineage_generation",
                obligation_type="invariant",
                description=(
                    "A repeated r2 repair supersedes the latest active r1 rather than replacing the original again, "
                    "preserves one stable root, records the previous repair node/packet/result/recheck and new delta, "
                    "increments attempt and generation exactly by one, returns to the declared gate, and cannot cycle."
                ),
                required_test_kinds=(REPLAY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "unified_repair.terminal_shared_engine",
                obligation_type="refinement",
                description=(
                    "Terminal backward replay adds a coordinating supplemental contract but delegates substantive "
                    "work to the same ordinary repair transaction, Worker, FlowGuard, Reviewer, PM, and replay engine."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "unified_repair.terminal_round_cap_three",
                obligation_type="hazard",
                description=(
                    "Terminal supplemental repair opens at most three coordinated rounds, never opens a fourth round, "
                    "and does not treat exhaustion as successful closure."
                ),
                required_test_kinds=(EDGE, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "unified_repair.completed_run_distinct_current_import",
                obligation_type="transition",
                description=(
                    "A late defect discovered after completion or stop creates a distinct current run, imports the "
                    "historical output only as read-only context, and never reactivates the old run's control state."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "unified_repair.action_runtime_refinement",
                obligation_type="refinement",
                description=(
                    "Every model action has one explicit runtime refinement row: repair_same_slot -> "
                    "repair_current_scope; repair_parent_scope -> repair_parent_scope; repair_subtree -> "
                    "repair_parent_scope with an explicit supersede-descendants scope contract; redesign_route -> "
                    "redesign_route; authorized_waiver -> waive_with_authority; and stop_for_user -> stop_for_user. "
                    "Unknown, missing, or ambiguous mappings block before runtime effect selection."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
        ),
        code_contracts=(
            _contract(
                "unified_repair.runtime.pm_historical_direct_entry",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="ensure_pm_historical_repair_decision_packet",
                implements=("unified_repair.pm_historical_direct_entry_no_blocker",),
                external_inputs=(
                    "ledger",
                    "historical_target_node_id",
                    "defect_summary",
                    "impact_summary",
                    "evidence_refs",
                ),
                external_outputs=("pm_repair_decision_packet_id",),
                state_reads=("route_nodes", "execution_frontier", "pm_repair_decisions"),
                state_writes=("packets", "pm_repair_decisions"),
                error_paths=("missing_defect_observation", "noncurrent_historical_target", "fabricated_blocker_prerequisite"),
            ),
            _contract(
                "unified_repair.runtime.same_slot_single_authority",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_replace_route_node_for_repair",
                implements=("unified_repair.same_slot_replacement_single_authority",),
                external_inputs=(
                    "ledger",
                    "node_id",
                    "logical_parent_id",
                    "business_intent_id",
                    "logical_slot_id",
                    "disposition_id",
                    "reason",
                ),
                external_outputs=("active_replacement_node_id",),
                state_reads=("route_nodes", "routes", "active_route_version"),
                state_writes=("route_nodes", "routes", "active_route_version", "execution_frontier"),
                error_paths=("historical_node_mutated", "logical_slot_drift", "multiple_active_authorities"),
            ),
            _contract(
                "unified_repair.runtime.repair_child_active_parent",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_materialize_parent_repair_child_nodes",
                implements=("unified_repair.repair_child_under_active_replacement",),
                external_inputs=("ledger", "replacement_id", "source_parent", "contract", "route_version"),
                external_outputs=(
                    "active_repair_child_node_ids",
                    "active_route_node_order",
                    "final_ledger_child_entry_ids",
                    "terminal_target_child_ids",
                ),
                state_reads=("route_nodes", "routes", "final_route_wide_gate_ledger", "terminal_backward_replay"),
                state_writes=(
                    "route_nodes",
                    "routes.node_order",
                    "final_route_wide_gate_ledger",
                    "terminal_backward_replay.segment_targets",
                ),
                side_effects=("worker_packet_issued", "child_result_accepted", "parent_closure_consumed_child"),
                error_paths=(
                    "child_attached_to_superseded_parent",
                    "duplicate_child_id",
                    "missing_replacement_parent",
                    "child_missing_from_active_order",
                    "child_missing_worker_result_or_acceptance",
                    "child_missing_from_final_or_terminal_projection",
                    "parent_closed_without_child",
                ),
            ),
            _contract(
                "unified_repair.runtime.worker_flowguard_reviewer_handoff",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_ensure_review_packet_for_task_result",
                implements=("unified_repair.worker_flowguard_reviewer_chain",),
                external_inputs=("ledger", "subject_id", "repair_generation", "force_new", "repair_blocker_id", "recheck_reason"),
                external_outputs=("review_packet_id",),
                state_reads=("packets", "results", "flowguard_work_orders", "source_generation", "route_nodes"),
                state_writes=("packets", "active_blockers"),
                error_paths=("reviewer_before_worker", "reviewer_before_flowguard", "flowguard_generation_mismatch"),
            ),
            _contract(
                "unified_repair.runtime.generation_currentness",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_node_final_quality_evidence_valid",
                implements=("unified_repair.contract_evidence_generation",),
                external_inputs=("ledger", "node", "repair_contract_generation"),
                external_outputs=("current_generation_valid",),
                state_reads=(
                    "source_generation",
                    "route_nodes.repair_generation",
                    "results",
                    "flowguard_work_orders",
                    "reviews",
                    "pm_dispositions",
                ),
                error_paths=("pre_contract_evidence", "stale_repair_generation", "mixed_generation_closure"),
            ),
            _contract(
                "unified_repair.runtime.decision_gate_effect_commit",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_apply_staged_pm_decision_gate",
                implements=("unified_repair.decision_gate_before_effect_commit",),
                external_inputs=(
                    "ledger",
                    "gate",
                    "system_closure_id",
                    "pre_effect_review_id",
                    "post_worker_review_id",
                ),
                external_outputs=("committed_effect_id", "opened_worker_packet_id"),
                state_reads=(
                    "pm_decision_gates.status",
                    "pm_decision_gates.flowguard_order_id",
                    "pm_decision_gates.pm_flowguard_acceptance_result_id",
                    "pm_decision_gates.review_id",
                    "pm_decision_gates.validation_evidence_id",
                    "pm_decision_gates.system_closure_id",
                    "pm_decision_gates.staged_effect",
                    "terminal_supplemental_repair.round",
                ),
                state_writes=(
                    "pm_decision_gates",
                    "staged_effect.status",
                    "packets",
                    "terminal_supplemental_repair",
                ),
                side_effects=("staged_effect_committed", "worker_packet_opened_after_gate"),
                error_paths=(
                    "gate_not_system_validated",
                    "pre_effect_and_worker_review_conflated",
                    "rejected_gate_committed",
                    "cancelled_gate_opened_worker",
                    "orphan_staged_effect",
                    "rejected_gate_consumed_terminal_round",
                ),
            ),
            _contract(
                "unified_repair.runtime.member_conservation",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_active_route_node_records",
                implements=("unified_repair.unaffected_sibling_rebind_conservation",),
                external_inputs=("ledger", "expected_effective_member_ids", "include_superseded"),
                external_outputs=("effective_active_route_node_records", "missing_member_ids", "extra_member_ids"),
                state_reads=("route_nodes", "routes", "active_route_version", "route_mutations"),
                error_paths=("unaffected_sibling_not_rebound", "effective_member_loss", "superseded_member_reactivated"),
            ),
            _contract(
                "unified_repair.runtime.downstream_replay",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_advance_frontier_after_node_acceptance",
                implements=("unified_repair.affected_downstream_replay",),
                external_inputs=(
                    "ledger",
                    "node_id",
                    "repair_action",
                    "affected_dependency_cone",
                    "same_slot_parent_or_downstream_impact",
                ),
                external_outputs=("replay_obligation_ids", "next_active_node_id"),
                state_reads=("execution_frontier", "route_nodes", "routes", "route_mutations"),
                state_writes=("execution_frontier", "route_nodes", "parent_backward_replays"),
                error_paths=(
                    "affected_downstream_not_replayed",
                    "parent_replay_skipped",
                    "same_slot_impact_replay_skipped",
                    "unaffected_evidence_invalidated",
                ),
            ),
            _contract(
                "unified_repair.runtime.repeated_lineage",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_record_repair_transaction",
                implements=("unified_repair.repeated_lineage_generation",),
                external_inputs=(
                    "ledger",
                    "blocker_or_defect",
                    "decision_id",
                    "source_id",
                    "fresh_packet_id",
                    "repair_root_id",
                    "previous_repair_transaction_id",
                    "latest_active_repair_transaction_id",
                    "previous_attempt",
                    "previous_generation",
                    "repair_delta",
                    "return_gate_id",
                ),
                external_outputs=(
                    "repair_transaction_id",
                    "superseded_previous_repair_transaction_id",
                    "attempt",
                    "generation",
                ),
                state_reads=("repair_transactions", "route_nodes", "packets", "results"),
                state_writes=("repair_transactions", "repair_transactions.status"),
                error_paths=(
                    "lineage_root_changed",
                    "previous_repair_missing",
                    "latest_active_repair_not_superseded",
                    "original_replaced_again",
                    "attempt_not_previous_plus_one",
                    "generation_not_previous_plus_one",
                    "repair_lineage_cycle",
                    "repair_delta_missing",
                ),
            ),
            _contract(
                "unified_repair.runtime.terminal_shared_adapter",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_record_terminal_supplemental_repair_contract",
                implements=("unified_repair.terminal_shared_engine",),
                external_inputs=("ledger", "payload", "source_result_id", "ordinary_repair_transaction_id"),
                external_outputs=("supplemental_contract_id", "ordinary_repair_trigger"),
                state_reads=("terminal_supplemental_repair", "supplemental_repair_contracts", "repair_transactions"),
                state_writes=("terminal_supplemental_repair", "supplemental_repair_contracts"),
                error_paths=("terminal_parallel_repair_shortcut", "terminal_contract_not_projected", "terminal_replay_not_rerun"),
            ),
            _contract(
                "unified_repair.runtime.terminal_round_cap",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_terminal_supplemental_rounds_exhausted",
                implements=("unified_repair.terminal_round_cap_three",),
                external_inputs=("ledger",),
                external_outputs=("rounds_exhausted",),
                state_reads=("terminal_supplemental_repair.round", "terminal_supplemental_repair.max_rounds"),
                error_paths=("fourth_round_opened", "exhaustion_treated_as_closure"),
            ),
            _contract(
                "unified_repair.runtime.completed_run_bridge",
                path="skills/flowpilot/assets/flowpilot_core_runtime/run_shell.py",
                symbol="create_historical_repair_run_shell",
                implements=(
                    "unified_repair.completed_run_distinct_current_import",
                ),
                external_inputs=(
                    "project_root",
                    "source_run_id",
                    "goal",
                    "acceptance_contract",
                    "run_id",
                ),
                external_outputs=(
                    "new_current_run_shell",
                    "read_only_imported_evidence_ids",
                ),
                state_reads=(
                    "source_run_ledger",
                    "source_run_terminal_lifecycle",
                    "source_run_results",
                ),
                state_writes=(
                    "new_run_ledger",
                    "historical_repair_intake",
                    "current_run_pointer",
                ),
                error_paths=(
                    "source_run_not_terminal",
                    "new_run_id_matches_source",
                    "old_control_state_reactivated",
                    "imported_evidence_mutable",
                ),
            ),
            _contract(
                "unified_repair.runtime.action_runtime_refinement",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_apply_pm_repair_decision",
                implements=("unified_repair.action_runtime_refinement",),
                external_inputs=(
                    "ledger",
                    "blocker_or_defect_id",
                    "decision_id",
                    "model_repair_action",
                    "action_refinement_mapping_id",
                    "scope_contract",
                ),
                external_outputs=("selected_runtime_decision", "validated_scope_contract"),
                state_reads=("repair_action_refinement_map", "pm_repair_decisions", "route_nodes", "active_blockers"),
                state_writes=("pm_repair_decisions.runtime_refinement",),
                error_paths=(
                    "missing_action_refinement",
                    "unknown_model_action",
                    "unknown_runtime_decision",
                    "ambiguous_action_refinement",
                    "repair_subtree_scope_contract_missing",
                ),
            ),
        ),
        test_evidence=tuple(
            _evidence(
                f"unified_repair.native.{suffix}.{test_kind}",
                test_name=test_name,
                path=test_path,
                command=command,
                test_kind=test_kind,
                covers=(obligation_id,),
                code_contracts=(contract_id,),
            )
            for obligation_id, contract_id, suffix, test_specs in (
                (
                    "unified_repair.pm_historical_direct_entry_no_blocker",
                    "unified_repair.runtime.pm_historical_direct_entry",
                    "pm_historical_direct_entry_no_blocker",
                    (
                        (
                            HAPPY,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_historical_intake_requires_evidence_and_creates_no_blocker",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_historical_intake_requires_evidence_and_creates_no_blocker -q",
                        ),
                        (
                            NEGATIVE,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_pm_repair_packet_rejects_missing_or_unknown_trigger_origin",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_pm_repair_packet_rejects_missing_or_unknown_trigger_origin -q",
                        ),
                    ),
                ),
                (
                    "unified_repair.same_slot_replacement_single_authority",
                    "unified_repair.runtime.same_slot_single_authority",
                    "same_slot_replacement_single_authority",
                    (
                        (
                            HAPPY,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_staged_historical_repair_has_no_early_effect_then_commits_same_slot",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_staged_historical_repair_has_no_early_effect_then_commits_same_slot -q",
                        ),
                        (
                            NEGATIVE,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_apply_preflight_failure_disposes_effect_and_leaves_no_partial_repair",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_apply_preflight_failure_disposes_effect_and_leaves_no_partial_repair -q",
                        ),
                    ),
                ),
                (
                    "unified_repair.repair_child_under_active_replacement",
                    "unified_repair.runtime.repair_child_active_parent",
                    "repair_child_under_active_replacement",
                    (
                        (
                            HAPPY,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_structured_subtree_places_repair_children_under_active_replacement",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_structured_subtree_places_repair_children_under_active_replacement -q",
                        ),
                        (
                            NEGATIVE,
                            "tests/test_flowpilot_high_standard_control_flow.py",
                            "test_pm_repair_parent_scope_requires_structured_repair_child_specs",
                            "python -m pytest tests/test_flowpilot_high_standard_control_flow.py::FlowPilotHighStandardControlFlowTests::test_pm_repair_parent_scope_requires_structured_repair_child_specs -q",
                        ),
                    ),
                ),
                (
                    "unified_repair.worker_flowguard_reviewer_chain",
                    "unified_repair.runtime.worker_flowguard_reviewer_handoff",
                    "worker_flowguard_reviewer_chain",
                    (
                        (
                            HAPPY,
                            "tests/test_flowpilot_core_runtime.py",
                            "test_terminal_replay_repair_current_scope_preserves_targets_and_closes",
                            "python -m pytest tests/test_flowpilot_core_runtime.py::FlowPilotCoreRuntimeTests::test_terminal_replay_repair_current_scope_preserves_targets_and_closes -q",
                        ),
                        (
                            NEGATIVE,
                            "tests/test_flowpilot_core_runtime.py",
                            "test_terminal_replay_block_branch_requires_repair_evidence",
                            "python -m pytest tests/test_flowpilot_core_runtime.py::FlowPilotCoreRuntimeTests::test_terminal_replay_block_branch_requires_repair_evidence -q",
                        ),
                    ),
                ),
                (
                    "unified_repair.contract_evidence_generation",
                    "unified_repair.runtime.generation_currentness",
                    "contract_evidence_generation",
                    (
                        (
                            NEGATIVE,
                            "tests/test_flowpilot_core_runtime.py",
                            "test_terminal_repair_evidence_rejects_wrong_or_early_contract_generation_identity",
                            "python -m pytest tests/test_flowpilot_core_runtime.py::FlowPilotCoreRuntimeTests::test_terminal_repair_evidence_rejects_wrong_or_early_contract_generation_identity -q",
                        ),
                        (
                            REPLAY,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_terminal_replacement_projects_committed_supplemental_contract_without_preseeding_source",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_terminal_replacement_projects_committed_supplemental_contract_without_preseeding_source -q",
                        ),
                    ),
                ),
                (
                    "unified_repair.decision_gate_before_effect_commit",
                    "unified_repair.runtime.decision_gate_effect_commit",
                    "decision_gate_before_effect_commit",
                    (
                        (
                            HAPPY,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_staged_historical_repair_has_no_early_effect_then_commits_same_slot",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_staged_historical_repair_has_no_early_effect_then_commits_same_slot -q",
                        ),
                        (
                            NEGATIVE,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_apply_preflight_failure_disposes_effect_and_leaves_no_partial_repair",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_apply_preflight_failure_disposes_effect_and_leaves_no_partial_repair -q",
                        ),
                    ),
                ),
                (
                    "unified_repair.unaffected_sibling_rebind_conservation",
                    "unified_repair.runtime.member_conservation",
                    "unaffected_sibling_rebind_conservation",
                    (
                        (
                            EDGE,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_route_repair_rebinds_unaffected_siblings_into_new_effective_route",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_route_repair_rebinds_unaffected_siblings_into_new_effective_route -q",
                        ),
                        (
                            NEGATIVE,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_dependency_cone_fails_closed_for_unknown_or_cyclic_topology",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_dependency_cone_fails_closed_for_unknown_or_cyclic_topology -q",
                        ),
                    ),
                ),
                (
                    "unified_repair.affected_downstream_replay",
                    "unified_repair.runtime.downstream_replay",
                    "affected_downstream_replay",
                    (
                        (
                            REPLAY,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_nested_dependency_cone_invalidates_only_ancestors_and_preserves_parallel_siblings",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_nested_dependency_cone_invalidates_only_ancestors_and_preserves_parallel_siblings -q",
                        ),
                        (
                            NEGATIVE,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_dependency_cone_fails_closed_for_unknown_or_cyclic_topology",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_dependency_cone_fails_closed_for_unknown_or_cyclic_topology -q",
                        ),
                    ),
                ),
                (
                    "unified_repair.repeated_lineage_generation",
                    "unified_repair.runtime.repeated_lineage",
                    "repeated_lineage_generation",
                    (
                        (
                            REPLAY,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_repeated_repair_targets_latest_generation_and_keeps_stable_root",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_repeated_repair_targets_latest_generation_and_keeps_stable_root -q",
                        ),
                        (
                            NEGATIVE,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_repeated_repair_lineage_is_mechanically_bound_to_the_failed_attempt",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_repeated_repair_lineage_is_mechanically_bound_to_the_failed_attempt -q",
                        ),
                    ),
                ),
                (
                    "unified_repair.terminal_shared_engine",
                    "unified_repair.runtime.terminal_shared_adapter",
                    "terminal_shared_engine",
                    (
                        (
                            HAPPY,
                            "tests/test_flowpilot_core_runtime.py",
                            "test_terminal_replay_repair_current_scope_preserves_targets_and_closes",
                            "python -m pytest tests/test_flowpilot_core_runtime.py::FlowPilotCoreRuntimeTests::test_terminal_replay_repair_current_scope_preserves_targets_and_closes -q",
                        ),
                        (
                            NEGATIVE,
                            "tests/test_flowpilot_core_runtime.py",
                            "test_terminal_replay_block_branch_requires_repair_evidence",
                            "python -m pytest tests/test_flowpilot_core_runtime.py::FlowPilotCoreRuntimeTests::test_terminal_replay_block_branch_requires_repair_evidence -q",
                        ),
                    ),
                ),
                (
                    "unified_repair.terminal_round_cap_three",
                    "unified_repair.runtime.terminal_round_cap",
                    "terminal_round_cap_three",
                    (
                        (
                            EDGE,
                            "tests/test_flowpilot_core_runtime.py",
                            "test_terminal_supplemental_repair_exhausts_after_third_round_without_pm_packet",
                            "python -m pytest tests/test_flowpilot_core_runtime.py::FlowPilotCoreRuntimeTests::test_terminal_supplemental_repair_exhausts_after_third_round_without_pm_packet -q",
                        ),
                        (
                            NEGATIVE,
                            "tests/test_flowpilot_core_runtime.py",
                            "test_stale_terminal_pm_packet_cannot_create_a_fourth_round_or_reissue",
                            "python -m pytest tests/test_flowpilot_core_runtime.py::FlowPilotCoreRuntimeTests::test_stale_terminal_pm_packet_cannot_create_a_fourth_round_or_reissue -q",
                        ),
                    ),
                ),
                (
                    "unified_repair.completed_run_distinct_current_import",
                    "unified_repair.runtime.completed_run_bridge",
                    "completed_run_distinct_current_import",
                    (
                        (
                            HAPPY,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_completed_run_repair_creates_distinct_current_run_with_read_only_imports",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_completed_run_repair_creates_distinct_current_run_with_read_only_imports -q",
                        ),
                        (
                            NEGATIVE,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_completed_run_repair_creates_distinct_current_run_with_read_only_imports",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_completed_run_repair_creates_distinct_current_run_with_read_only_imports -q",
                        ),
                    ),
                ),
                (
                    "unified_repair.action_runtime_refinement",
                    "unified_repair.runtime.action_runtime_refinement",
                    "action_runtime_refinement",
                    (
                        (
                            HAPPY,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_historical_waiver_and_stop_are_packet_free_explicit_pm_dispositions",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_historical_waiver_and_stop_are_packet_free_explicit_pm_dispositions -q",
                        ),
                        (
                            NEGATIVE,
                            "tests/test_flowpilot_unified_repair_runtime.py",
                            "test_pm_repair_packet_rejects_missing_or_unknown_trigger_origin",
                            "python -m pytest tests/test_flowpilot_unified_repair_runtime.py::test_pm_repair_packet_rejects_missing_or_unknown_trigger_origin -q",
                        ),
                    ),
                ),
            )
            for test_kind, test_path, test_name, command in test_specs
        ),
    )

    currentness_field_projections = (
        _field_projection(
            "field_lifecycle_currentness.packet_status_terminal_monotonic",
            field_id="packet.status",
            obligation_id="field_lifecycle_currentness.packet_terminal_monotonic",
            code_contract_id="field_lifecycle_currentness.runtime.submit_result_terminal_packet_preservation",
            required_test_kinds=(NEGATIVE, REPLAY),
            state_reads=("packet.status", "packet.accepted_result_id", "lease.status"),
            state_writes=("results", "packet.result_ids", "packet.status"),
            side_effects=("result_recorded",),
            error_paths=("noncurrent_packet", "duplicate_after_packet_accepted"),
            rationale="Late results may be recorded as audit history but cannot reactivate terminal packet status.",
        ),
        _field_projection(
            "field_lifecycle_currentness.packet_result_history_append_only",
            field_id="packet.result_ids",
            obligation_id="field_lifecycle_currentness.result_history_append_only",
            code_contract_id="field_lifecycle_currentness.runtime.submit_result_audit_append",
            required_test_kinds=(HAPPY, REPLAY),
            state_reads=("packet.result_ids",),
            state_writes=("packet.result_ids", "results"),
            side_effects=("result_recorded",),
            rationale="Result history remains append-only audit evidence even when the packet is noncurrent.",
        ),
        _field_projection(
            "field_lifecycle_currentness.accepted_result_pointer_single_commit",
            field_id="packet.accepted_result_id",
            obligation_id="field_lifecycle_currentness.accepted_result_pointer_single_commit",
            code_contract_id="field_lifecycle_currentness.runtime.accept_packet_result_commit",
            required_test_kinds=(HAPPY, NEGATIVE),
            state_reads=("packet.accepted_result_id", "result.status"),
            state_writes=("packet.accepted_result_id", "packet.status", "result.status"),
            side_effects=("lease_closed",),
            error_paths=("duplicate_after_packet_accepted",),
            rationale="Accepted result pointer has one runtime commit point and is not reassigned by duplicates.",
        ),
        _field_projection(
            "field_lifecycle_currentness.pending_route_mutation_until_commit",
            field_id="execution_frontier.pending_route_mutation",
            obligation_id="field_lifecycle_currentness.pending_route_mutation_disposition",
            code_contract_id="field_lifecycle_currentness.runtime.frontier_pending_mutation_commit",
            required_test_kinds=(EDGE, NEGATIVE),
            state_reads=("execution_frontier.pending_route_mutation", "route_nodes.status"),
            state_writes=("execution_frontier.pending_route_mutation", "route_mutations"),
            side_effects=("execution_frontier_updated",),
            rationale="Pending route mutation must clear or terminally disposition after replacement node acceptance.",
        ),
        _field_projection(
            "field_lifecycle_currentness.active_packets_derived_projection",
            field_id="active_packets",
            obligation_id="field_lifecycle_currentness.active_packets_derive_from_currentness",
            code_contract_id="field_lifecycle_currentness.runtime.current_packets_for_routing",
            required_test_kinds=(NEGATIVE, REPLAY),
            state_reads=("packets", "route_nodes", "active_route_version"),
            state_writes=(),
            side_effects=("status_projection", "router_next_action"),
            error_paths=("stale_route_version", "noncurrent_route_node"),
            rationale="Router and compact active-packet views must use the single Router currentness predicate.",
        ),
        _field_projection(
            "field_lifecycle_currentness.closure_accepted_packets_derived_projection",
            field_id="closure_accepted_packets",
            obligation_id="field_lifecycle_currentness.closure_accepted_packets_derive_from_accepted_evidence",
            code_contract_id="field_lifecycle_currentness.runtime.accepted_packets_for_closure_evidence",
            required_test_kinds=(HAPPY, NEGATIVE),
            state_reads=("packets", "route_nodes", "active_route_version", "packet.accepted_result_id"),
            state_writes=(),
            side_effects=("final_closure", "backward_chain"),
            error_paths=("accepted_packet_lost_from_closure", "superseded_node_evidence_reused"),
            rationale="Final closure uses accepted packet-result evidence without reactivating those packets for routing.",
        ),
        _field_projection(
            "field_lifecycle_currentness.accepted_result_packets_derived_projection",
            field_id="accepted_result_packets",
            obligation_id="field_lifecycle_currentness.accepted_result_packets_derive_from_active_route",
            code_contract_id="field_lifecycle_currentness.runtime.accepted_result_packets_for_active_route",
            required_test_kinds=(HAPPY, NEGATIVE),
            state_reads=("packets", "route_nodes", "active_route_version", "packet.accepted_result_id"),
            state_writes=(),
            side_effects=("accepted_packet_lease_health", "final_return_preflight"),
            error_paths=("stale_accepted_lease_not_detected", "stale_route_evidence_reused"),
            rationale="Accepted-result packet health checks must inspect active-route accepted-result authority without treating it as router-current work.",
        ),
        _field_projection(
            "field_lifecycle_currentness.route_authority_legal_actions_current",
            field_id="route_authority_snapshot.legal_action_ids",
            obligation_id="field_lifecycle_currentness.route_authority_legal_actions_current",
            code_contract_id="field_lifecycle_currentness.runtime.route_authority_snapshot",
            required_test_kinds=(HAPPY, NEGATIVE),
            state_reads=("execution_frontier", "route_action_policy_registry", "route_nodes", "run_state.flags"),
            side_effects=("legal_next_action_context",),
            error_paths=("wrong_path", "unsupported_event_alias"),
            rationale="Legal route-action ids must derive from the current frontier and policy registry, not from stale prompts or aliases.",
        ),
        _field_projection(
            "field_lifecycle_currentness.route_authority_single_owner_current",
            field_id="route_authority_snapshot.current_owner",
            obligation_id="field_lifecycle_currentness.route_authority_single_owner_current",
            code_contract_id="field_lifecycle_currentness.runtime.route_authority_snapshot",
            required_test_kinds=(HAPPY, NEGATIVE),
            state_reads=("route_action_policy_registry.owner_role", "route_action_policy_registry.actor_roles"),
            side_effects=("single_authority_projection",),
            error_paths=("owner_missing", "owner_conflict", "role_overreach"),
            rationale="The current legal route action set must expose exactly one owner or block as owner_missing/owner_conflict.",
        ),
        _field_projection(
            "field_lifecycle_currentness.route_authority_required_repair_command_current",
            field_id="route_authority_snapshot.required_repair_command",
            obligation_id="field_lifecycle_currentness.route_authority_required_repair_command_current",
            code_contract_id="field_lifecycle_currentness.runtime.route_authority_snapshot",
            required_test_kinds=(NEGATIVE, REPLAY),
            state_reads=("route_action_policy_registry.required_repair_command",),
            side_effects=("route_authority_rejection_feedback",),
            error_paths=("wrong_path", "fallback_payload", "no_delta_retry"),
            rationale="Rejected packages must receive the current legal repair command so the next package can change shape instead of looping.",
        ),
        _field_projection(
            "field_lifecycle_currentness.route_authority_rejection_blocker_current",
            field_id="active_control_blocker.route_authority_rejection",
            obligation_id="field_lifecycle_currentness.route_authority_rejection_blocker_current",
            code_contract_id="field_lifecycle_currentness.runtime.write_route_authority_rejection_blocker",
            required_test_kinds=(NEGATIVE, REPLAY),
            state_reads=("execution_frontier", "route_action_policy_registry", "run_state.flags"),
            state_writes=("active_control_blocker", "control_blocker_artifact", "control_plane_indexes"),
            side_effects=("control_blocker_written", "run_state_saved"),
            error_paths=("wrong_path", "unsupported_payload_shape", "unsupported_event_alias"),
            rationale="Wrong-path and fallback-like submissions become a current control blocker with structured route-authority feedback, not prose or alias translation.",
        ),
    )
    currentness_field_lifecycle = ModelTestAlignmentPlan(
        model_id="field_lifecycle_currentness",
        obligations=(
            _obligation(
                "field_lifecycle_currentness.packet_terminal_monotonic",
                obligation_type="field_lifecycle",
                description="Packet terminal currentness states are absorbing for current authority when late results arrive.",
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_implementation=True,
            ),
            _obligation(
                "field_lifecycle_currentness.result_history_append_only",
                obligation_type="field_lifecycle",
                description="Packet result history appends late results as audit evidence without making them current authority.",
                required_test_kinds=(HAPPY, REPLAY),
                allow_shared_implementation=True,
            ),
            _obligation(
                "field_lifecycle_currentness.accepted_result_pointer_single_commit",
                obligation_type="field_lifecycle",
                description="Accepted result pointers are written by the runtime acceptance commit point and are not reassigned by duplicate output.",
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "field_lifecycle_currentness.pending_route_mutation_disposition",
                obligation_type="field_lifecycle",
                description="Pending route mutation state clears or terminally dispositions after replacement frontier commit.",
                required_test_kinds=(EDGE, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "field_lifecycle_currentness.active_packets_derive_from_currentness",
                obligation_type="field_lifecycle",
                description="Derived active-packet views share the Router currentness predicate for route version, node status, and packet terminal status.",
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_implementation=True,
            ),
            _obligation(
                "field_lifecycle_currentness.closure_accepted_packets_derive_from_accepted_evidence",
                obligation_type="field_lifecycle",
                description="Final closure derives accepted packet evidence from current active-route accepted results, not from router-active packets.",
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "field_lifecycle_currentness.accepted_result_packets_derive_from_active_route",
                obligation_type="field_lifecycle",
                description="Accepted packet health checks derive active-route accepted-result targets separately from router-active packets.",
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "field_lifecycle_currentness.final_preflight_active_blockers_use_current_effective",
                obligation_type="field_lifecycle",
                description="Final return preflight derives active blocker targets from the current-effective blocker predicate, so accepted repair history cannot become current authority.",
                required_test_kinds=(NEGATIVE,),
                allow_shared_implementation=True,
            ),
            _obligation(
                "field_lifecycle_currentness.route_authority_legal_actions_current",
                obligation_type="field_lifecycle",
                description="Route-authority legal action ids derive from the current frontier and route action policy registry.",
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "field_lifecycle_currentness.route_authority_single_owner_current",
                obligation_type="field_lifecycle",
                description="Route-authority owner is a single current owner derived from legal action policy rows or blocks as owner_missing/owner_conflict.",
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "field_lifecycle_currentness.route_authority_required_repair_command_current",
                obligation_type="field_lifecycle",
                description="Rejected route-authority packages expose a current required repair command that guides the next package shape.",
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_implementation=True,
            ),
            _obligation(
                "field_lifecycle_currentness.route_authority_rejection_blocker_current",
                obligation_type="field_lifecycle",
                description="Wrong-path, old-alias, and fallback-like route submissions write a current structured route-authority rejection blocker.",
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_implementation=True,
            ),
        ),
        code_contracts=(
            _contract(
                "field_lifecycle_currentness.runtime.submit_result_terminal_packet_preservation",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="submit_result",
                implements=("field_lifecycle_currentness.packet_terminal_monotonic",),
                external_inputs=("ledger", "lease_id", "packet_id", "body"),
                state_reads=("packet.status", "lease.status", "packet.accepted_result_id"),
                state_writes=("results", "packet.result_ids", "packet.status"),
                side_effects=("result_submitted_event",),
            ),
            _contract(
                "field_lifecycle_currentness.runtime.submit_result_audit_append",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="submit_result",
                implements=("field_lifecycle_currentness.result_history_append_only",),
                external_inputs=("ledger", "lease_id", "packet_id", "body"),
                state_reads=("packet.result_ids",),
                state_writes=("results", "packet.result_ids"),
                side_effects=("result_submitted_event",),
            ),
            _contract(
                "field_lifecycle_currentness.runtime.accept_packet_result_commit",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_accept_packet_result",
                implements=("field_lifecycle_currentness.accepted_result_pointer_single_commit",),
                external_inputs=("ledger", "packet", "result", "lease"),
                state_reads=("result.status",),
                state_writes=("packet.accepted_result_id", "packet.status", "result.status"),
                side_effects=("lease_closed",),
            ),
            _contract(
                "field_lifecycle_currentness.runtime.frontier_pending_mutation_commit",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_advance_frontier_after_node_acceptance",
                implements=("field_lifecycle_currentness.pending_route_mutation_disposition",),
                external_inputs=("ledger", "node_id"),
                state_reads=("execution_frontier.pending_route_mutation", "route_nodes.status"),
                state_writes=("execution_frontier.pending_route_mutation", "route_mutations"),
                side_effects=("execution_frontier_updated",),
            ),
            _contract(
                "field_lifecycle_currentness.runtime.current_packets_for_routing",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_current_packets_for_routing",
                implements=("field_lifecycle_currentness.active_packets_derive_from_currentness",),
                external_inputs=("ledger",),
                state_reads=("packets", "route_nodes", "active_route_version"),
                state_writes=(),
                side_effects=("derived_projection",),
            ),
            _contract(
                "field_lifecycle_currentness.runtime.accepted_packets_for_closure_evidence",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_accepted_packets_for_closure_evidence",
                implements=("field_lifecycle_currentness.closure_accepted_packets_derive_from_accepted_evidence",),
                external_inputs=("ledger",),
                state_reads=("packets", "route_nodes", "active_route_version", "packet.accepted_result_id"),
                state_writes=(),
                side_effects=("derived_projection",),
            ),
            _contract(
                "field_lifecycle_currentness.runtime.accepted_result_packets_for_active_route",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_accepted_result_packets_for_active_route",
                implements=("field_lifecycle_currentness.accepted_result_packets_derive_from_active_route",),
                external_inputs=("ledger",),
                state_reads=("packets", "route_nodes", "active_route_version", "packet.accepted_result_id"),
                state_writes=(),
                side_effects=("derived_projection",),
            ),
            _contract(
                "field_lifecycle_currentness.runtime.current_target_preflight_blockers",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_current_target_preflight_blockers",
                implements=("field_lifecycle_currentness.final_preflight_active_blockers_use_current_effective",),
                external_inputs=("ledger", "next_action"),
                state_reads=("active_blockers", "packets", "route_nodes", "active_route_version"),
                state_writes=(),
                side_effects=("final_return_preflight",),
            ),
            _contract(
                "field_lifecycle_currentness.runtime.route_authority_snapshot",
                path="skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion.py",
                symbol="_route_authority_snapshot",
                implements=(
                    "field_lifecycle_currentness.route_authority_legal_actions_current",
                    "field_lifecycle_currentness.route_authority_single_owner_current",
                    "field_lifecycle_currentness.route_authority_required_repair_command_current",
                ),
                external_inputs=("policy_by_id", "frontier", "active_node_kind", "legal_ids", "blocking_reasons"),
                external_outputs=("route_authority_snapshot",),
                state_reads=("route_action_policy_registry", "execution_frontier"),
                side_effects=("derived_projection",),
                error_paths=("owner_missing", "owner_conflict"),
            ),
            _contract(
                "field_lifecycle_currentness.runtime.write_route_authority_rejection_blocker",
                path="skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion.py",
                symbol="_write_route_authority_rejection_blocker",
                implements=("field_lifecycle_currentness.route_authority_rejection_blocker_current",),
                external_inputs=("rejected_action_id", "context", "rejected_event", "rejection_kind"),
                external_outputs=("control_blocker",),
                state_reads=("execution_frontier", "route_action_policy_registry"),
                state_writes=("active_control_blocker", "control_blocker_artifact"),
                side_effects=("control_blocker_written", "control_plane_indexes_synced", "run_state_saved"),
                error_paths=("wrong_path", "unsupported_payload_shape", "unsupported_event_alias"),
            ),
        ),
        test_evidence=(
            _evidence(
                "field_lifecycle_currentness.negative.late_terminal_statuses",
                test_name="test_late_result_rejects_noncurrent_packet_statuses_without_mutation",
                path="tests/test_flowpilot_lifecycle_guard.py",
                command="python -m unittest tests.test_flowpilot_lifecycle_guard.FlowPilotLifecycleGuardTests.test_late_result_rejects_noncurrent_packet_statuses_without_mutation",
                test_kind=NEGATIVE,
                covers=("field_lifecycle_currentness.packet_terminal_monotonic",),
                code_contracts=("field_lifecycle_currentness.runtime.submit_result_terminal_packet_preservation",),
            ),
            _evidence(
                "field_lifecycle_currentness.happy.current_result_history_append",
                test_name="test_current_result_history_appends_on_open_packet",
                path="tests/test_flowpilot_lifecycle_guard.py",
                command="python -m unittest tests.test_flowpilot_lifecycle_guard.FlowPilotLifecycleGuardTests.test_current_result_history_appends_on_open_packet",
                test_kind=HAPPY,
                covers=("field_lifecycle_currentness.result_history_append_only",),
                code_contracts=("field_lifecycle_currentness.runtime.submit_result_audit_append",),
            ),
            _evidence(
                "field_lifecycle_currentness.replay.fake_host_late_result_audit",
                test_name="test_fake_host_late_result_is_rejected_without_reactivation",
                path="tests/test_flowpilot_lifecycle_guard.py",
                command="python -m unittest tests.test_flowpilot_lifecycle_guard.FlowPilotLifecycleGuardTests.test_fake_host_late_result_is_rejected_without_reactivation",
                test_kind=REPLAY,
                covers=(
                    "field_lifecycle_currentness.packet_terminal_monotonic",
                    "field_lifecycle_currentness.result_history_append_only",
                ),
                code_contracts=(
                    "field_lifecycle_currentness.runtime.submit_result_terminal_packet_preservation",
                    "field_lifecycle_currentness.runtime.submit_result_audit_append",
                ),
            ),
            _evidence(
                "field_lifecycle_currentness.happy.accept_pointer_commit",
                test_name="test_accept_packet_result_writes_single_pointer_on_current_commit",
                path="tests/test_flowpilot_lifecycle_guard.py",
                command="python -m unittest tests.test_flowpilot_lifecycle_guard.FlowPilotLifecycleGuardTests.test_accept_packet_result_writes_single_pointer_on_current_commit",
                test_kind=HAPPY,
                covers=("field_lifecycle_currentness.accepted_result_pointer_single_commit",),
                code_contracts=("field_lifecycle_currentness.runtime.accept_packet_result_commit",),
            ),
            _evidence(
                "field_lifecycle_currentness.negative.accepted_pointer_duplicate",
                test_name="test_duplicate_after_accepted_rejects_without_polluting_accepted_result_pointer",
                path="tests/test_flowpilot_lifecycle_guard.py",
                command="python -m unittest tests.test_flowpilot_lifecycle_guard.FlowPilotLifecycleGuardTests.test_duplicate_after_accepted_rejects_without_polluting_accepted_result_pointer",
                test_kind=NEGATIVE,
                covers=("field_lifecycle_currentness.accepted_result_pointer_single_commit",),
                code_contracts=("field_lifecycle_currentness.runtime.accept_packet_result_commit",),
            ),
            _evidence(
                "field_lifecycle_currentness.edge.pending_route_mutation_commit",
                test_name="test_pending_route_mutation_clears_after_replacement_node_acceptance",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_pending_route_mutation_clears_after_replacement_node_acceptance",
                test_kind=EDGE,
                covers=("field_lifecycle_currentness.pending_route_mutation_disposition",),
                code_contracts=("field_lifecycle_currentness.runtime.frontier_pending_mutation_commit",),
            ),
            _evidence(
                "field_lifecycle_currentness.negative.unmatched_pending_route_mutation_kept",
                test_name="test_unmatched_pending_route_mutation_survives_unrelated_node_acceptance",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_unmatched_pending_route_mutation_survives_unrelated_node_acceptance",
                test_kind=NEGATIVE,
                covers=("field_lifecycle_currentness.pending_route_mutation_disposition",),
                code_contracts=("field_lifecycle_currentness.runtime.frontier_pending_mutation_commit",),
            ),
            _evidence(
                "field_lifecycle_currentness.negative.active_projection_currentness",
                test_name="test_routing_projection_excludes_noncurrent_node_packets_without_blocking_closure",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_routing_projection_excludes_noncurrent_node_packets_without_blocking_closure",
                test_kind=NEGATIVE,
                covers=("field_lifecycle_currentness.active_packets_derive_from_currentness",),
                code_contracts=("field_lifecycle_currentness.runtime.current_packets_for_routing",),
            ),
            _evidence(
                "field_lifecycle_currentness.happy.closure_accepted_projection",
                test_name="test_closure_accepted_evidence_projection_keeps_accepted_node_packets",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_closure_accepted_evidence_projection_keeps_accepted_node_packets",
                test_kind=HAPPY,
                covers=(
                    "field_lifecycle_currentness.accepted_result_packets_derive_from_active_route",
                    "field_lifecycle_currentness.closure_accepted_packets_derive_from_accepted_evidence",
                ),
                code_contracts=(
                    "field_lifecycle_currentness.runtime.accepted_result_packets_for_active_route",
                    "field_lifecycle_currentness.runtime.accepted_packets_for_closure_evidence",
                ),
            ),
            _evidence(
                "field_lifecycle_currentness.negative.closure_superseded_projection",
                test_name="test_closure_accepted_evidence_projection_excludes_superseded_node_packets",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_closure_accepted_evidence_projection_excludes_superseded_node_packets",
                test_kind=NEGATIVE,
                covers=("field_lifecycle_currentness.closure_accepted_packets_derive_from_accepted_evidence",),
                code_contracts=("field_lifecycle_currentness.runtime.accepted_packets_for_closure_evidence",),
            ),
            _evidence(
                "field_lifecycle_currentness.negative.accepted_result_health_stale_lease",
                test_name="test_final_preflight_blocks_stale_active_accepted_packet_lease",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_final_preflight_blocks_stale_active_accepted_packet_lease",
                test_kind=NEGATIVE,
                covers=("field_lifecycle_currentness.accepted_result_packets_derive_from_active_route",),
                code_contracts=("field_lifecycle_currentness.runtime.accepted_result_packets_for_active_route",),
            ),
            _evidence(
                "field_lifecycle_currentness.replay.quarantined_projection_currentness",
                test_name="test_quarantined_packet_rejects_late_submit_and_stays_out_of_active_projection",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_quarantined_packet_rejects_late_submit_and_stays_out_of_active_projection",
                test_kind=REPLAY,
                covers=("field_lifecycle_currentness.active_packets_derive_from_currentness",),
                code_contracts=("field_lifecycle_currentness.runtime.current_packets_for_routing",),
            ),
            _evidence(
                "field_lifecycle_currentness.negative.final_preflight_accepted_repair_history",
                test_name="test_final_preflight_ignores_accepted_noncurrent_repair_packet_open_blocker",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_final_preflight_ignores_accepted_noncurrent_repair_packet_open_blocker",
                test_kind=NEGATIVE,
                covers=("field_lifecycle_currentness.final_preflight_active_blockers_use_current_effective",),
                code_contracts=("field_lifecycle_currentness.runtime.current_target_preflight_blockers",),
            ),
            _evidence(
                "field_lifecycle_currentness.happy.route_authority_snapshot",
                test_name="run_flowpilot_route_authority_singularity_checks",
                path="simulations/run_flowpilot_route_authority_singularity_checks.py",
                command="python simulations/run_flowpilot_route_authority_singularity_checks.py --json-out simulations/flowpilot_route_authority_singularity_results.json",
                test_kind=HAPPY,
                covers=(
                    "field_lifecycle_currentness.route_authority_legal_actions_current",
                    "field_lifecycle_currentness.route_authority_single_owner_current",
                ),
                code_contracts=("field_lifecycle_currentness.runtime.route_authority_snapshot",),
            ),
            _evidence(
                "field_lifecycle_currentness.negative.route_authority_rejections",
                test_name="RouteMutationParentBackwardRuntimeTests route-authority rejection tests",
                path="tests/router_runtime/route_mutation_parent_backward.py",
                command="python -m unittest tests.router_runtime.route_mutation_parent_backward.RouteMutationParentBackwardRuntimeTests",
                test_kind=NEGATIVE,
                covers=(
                    "field_lifecycle_currentness.route_authority_legal_actions_current",
                    "field_lifecycle_currentness.route_authority_single_owner_current",
                    "field_lifecycle_currentness.route_authority_required_repair_command_current",
                    "field_lifecycle_currentness.route_authority_rejection_blocker_current",
                ),
                code_contracts=(
                    "field_lifecycle_currentness.runtime.route_authority_snapshot",
                    "field_lifecycle_currentness.runtime.write_route_authority_rejection_blocker",
                ),
            ),
            _evidence(
                "field_lifecycle_currentness.replay.route_authority_corrected_retry",
                test_name="test_route_authority_wrong_path_rejection_guides_corrected_retry_fake_package",
                path="tests/test_flowpilot_synthetic_agent_trace_replay.py",
                command="python -m unittest tests.test_flowpilot_synthetic_agent_trace_replay.FlowPilotSyntheticExceptionTraceReplayTests.test_route_authority_wrong_path_rejection_guides_corrected_retry_fake_package",
                test_kind=REPLAY,
                covers=(
                    "field_lifecycle_currentness.route_authority_required_repair_command_current",
                    "field_lifecycle_currentness.route_authority_rejection_blocker_current",
                ),
                code_contracts=(
                    "field_lifecycle_currentness.runtime.route_authority_snapshot",
                    "field_lifecycle_currentness.runtime.write_route_authority_rejection_blocker",
                ),
            ),
        ),
        field_lifecycle_reports=(_currentness_field_lifecycle_report(currentness_field_projections),),
        field_lifecycle_projections=currentness_field_projections,
    )

    current_node_trunk = ModelTestAlignmentPlan(
        model_id="current_node_trunk_invariant",
        obligations=(
            _obligation(
                "current_node_trunk.ordinary_reviewer_worker_postflowguard_reviewer",
                obligation_type="invariant",
                description=(
                    "Every ordinary executable node follows the current trunk "
                    "invariant: PM node entry self-check -> ordinary node plan "
                    "Reviewer -> Worker -> post-result FlowGuard -> independent "
                    "Reviewer. Ordinary node entry does not require a pre-worker "
                    "FlowGuard packet."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "current_node_trunk.structural_route_flowguard_pm_absorption_reviewer",
                obligation_type="invariant",
                description=(
                    "Structural route changes require FlowGuard simulation, PM "
                    "absorption, and Reviewer before route mutation commit. PM "
                    "must rewrite and rerun FlowGuard when the FlowGuard report "
                    "blocks or PM changes the route plan after the report."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
        ),
        test_evidence=(
            _evidence(
                "current_node_trunk.happy.context_follows_worker_and_reviewer",
                test_name="test_node_context_package_follows_worker_postflowguard_and_reviewer_packets",
                path="tests/test_flowpilot_high_standard_control_flow.py",
                command="python -m unittest tests.test_flowpilot_high_standard_control_flow.FlowPilotHighStandardControlFlowTests.test_node_context_package_follows_worker_postflowguard_and_reviewer_packets",
                test_kind=HAPPY,
                covers=("current_node_trunk.ordinary_reviewer_worker_postflowguard_reviewer",),
            ),
            _evidence(
                "current_node_trunk.negative.ordinary_node_without_prework",
                test_name="test_ordinary_node_acceptance_plan_releases_worker_without_prework_flowguard",
                path="tests/test_flowpilot_high_standard_control_flow.py",
                command="python -m unittest tests.test_flowpilot_high_standard_control_flow.FlowPilotHighStandardControlFlowTests.test_ordinary_node_acceptance_plan_releases_worker_without_prework_flowguard",
                test_kind=NEGATIVE,
                covers=("current_node_trunk.ordinary_reviewer_worker_postflowguard_reviewer",),
            ),
            _evidence(
                "current_node_trunk.negative.structural_flowguard_block",
                test_name="test_node_acceptance_redesign_route_flowguard_block_prevents_route_mutation",
                path="tests/test_flowpilot_high_standard_control_flow.py",
                command="python -m unittest tests.test_flowpilot_high_standard_control_flow.FlowPilotHighStandardControlFlowTests.test_node_acceptance_redesign_route_flowguard_block_prevents_route_mutation",
                test_kind=NEGATIVE,
                covers=("current_node_trunk.structural_route_flowguard_pm_absorption_reviewer",),
            ),
            _evidence(
                "current_node_trunk.happy.pm_absorption_required",
                test_name="test_node_acceptance_redesign_route_requires_pm_absorption_before_reviewer",
                path="tests/test_flowpilot_high_standard_control_flow.py",
                command="python -m unittest tests.test_flowpilot_high_standard_control_flow.FlowPilotHighStandardControlFlowTests.test_node_acceptance_redesign_route_requires_pm_absorption_before_reviewer",
                test_kind=HAPPY,
                covers=("current_node_trunk.structural_route_flowguard_pm_absorption_reviewer",),
            ),
        ),
    )

    terminal_closure_resume = ModelTestAlignmentPlan(
        model_id="terminal_closure_resume",
        obligations=(
            _obligation(
                "terminal.final_ledger_and_backward_replay",
                obligation_type="invariant",
                description="Terminal completion requires a clean PM-built final ledger, delivered-product backward replay, and PM completion approval.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "closure.dirty_ledgers_block_completion",
                obligation_type="hazard",
                description="Closure blocks dirty defect, PM-suggestion, role-memory, quarantine, or source-of-truth state after terminal replay.",
                required_test_kinds=(FAILURE,),
            ),
            _obligation(
                "terminal.final_quality_current_evidence_gates",
                obligation_type="invariant",
                description="Final ledger, requirement matrix, terminal replay, and closure count only current accepted review, passing FlowGuard, passing validation, active-route evidence, and exact runtime-issued replay segments.",
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "terminal.runtime_hard_gate_escape_return_path",
                obligation_type="transition",
                description="Runtime hard-gate escapes found before terminal replay return to the owning normal gate, with ancestor node-entry gates prioritized before descendants and terminal quality review reachable only after hard gates are clean.",
                required_test_kinds=(HAPPY, NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "terminal.supplemental_repair_contract",
                obligation_type="invariant",
                description="Terminal Reviewer gaps that continue repair require a PM supplemental repair contract, owner repair-node projection, existing gates, final ledger/matrix rows, terminal replay segments, and a hard three-round cap.",
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "resume.current_run_reentry",
                obligation_type="transition",
                description="Resume re-entry loads current-run state, frontier, packet ledger, daemon/owner state, role memory, and recovery evidence before PM work.",
                required_test_kinds=(HAPPY, FAILURE),
            ),
        ),
        code_contracts=(
            _contract(
                "terminal.runtime.review_evidence_current_and_accepted",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_review_evidence_current_and_accepted",
                implements=("terminal.final_quality_current_evidence_gates",),
                external_inputs=("ledger", "review_id", "node_id"),
                external_outputs=("bool",),
                state_reads=("reviews", "results", "packets", "active_route_version"),
            ),
            _contract(
                "terminal.runtime.flowguard_order_current_and_passing",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_flowguard_order_current_and_passing",
                implements=("terminal.final_quality_current_evidence_gates",),
                external_inputs=("ledger", "order_id", "node_id"),
                external_outputs=("bool",),
                state_reads=("flowguard_work_orders", "packets", "source_generation", "active_route_version"),
            ),
            _contract(
                "terminal.runtime.validation_evidence_current_and_passing",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_validation_evidence_current_and_passing",
                implements=("terminal.final_quality_current_evidence_gates",),
                external_inputs=("ledger", "evidence_id", "node_id"),
                external_outputs=("bool",),
                state_reads=("validation_evidence", "packets", "source_generation", "active_route_version"),
            ),
            _contract(
                "terminal.runtime.final_requirement_evidence_matrix",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="build_final_requirement_evidence_matrix",
                implements=("terminal.final_quality_current_evidence_gates",),
                external_inputs=("ledger",),
                external_outputs=("final_requirement_evidence_matrix"),
                state_reads=("route_nodes", "reviews", "flowguard_work_orders", "validation_evidence"),
                state_writes=("final_requirement_evidence_matrix",),
            ),
            _contract(
                "terminal.runtime.terminal_backward_replay_result_contract",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_terminal_backward_replay_result_violation",
                implements=("terminal.final_quality_current_evidence_gates",),
                external_inputs=("packet", "result"),
                external_outputs=("contract_check",),
                state_reads=("packet.body.segment_targets", "result.body.segment_reviews"),
            ),
            _contract(
                "terminal.runtime.terminal_replay_current_scope_repair_packet",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_issue_current_scope_repair_packet",
                implements=("terminal.final_quality_current_evidence_gates", "terminal.supplemental_repair_contract"),
                external_inputs=("ledger", "blocker", "decision_id"),
                external_outputs=("packet_id",),
                state_reads=("active_blockers", "final_route_wide_gate_ledger", "final_requirement_evidence_matrix"),
                state_writes=("packets", "repair_transactions"),
            ),
            _contract(
                "terminal.runtime.parse_supplemental_repair_contract",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_parse_terminal_supplemental_repair_contract_payload",
                implements=("terminal.supplemental_repair_contract",),
                external_inputs=("ledger", "packet", "payload", "decision", "route_plan"),
                external_outputs=("supplemental_repair_contract"),
                state_reads=("active_blockers", "contract_hash", "acceptance_item_registry", "route_nodes"),
            ),
            _contract(
                "terminal.runtime.record_supplemental_repair_contract",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_record_terminal_supplemental_repair_contract",
                implements=("terminal.supplemental_repair_contract",),
                external_inputs=("ledger", "contract", "decision_id", "packet", "result"),
                external_outputs=("terminal_supplemental_repair"),
                state_reads=("supplemental_repair_contracts",),
                state_writes=("terminal_supplemental_repair", "supplemental_repair_contracts", "terminal_backward_replay_id"),
            ),
            _contract(
                "terminal.runtime.supplemental_repair_closure_rows",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_supplemental_repair_closure_rows",
                implements=("terminal.supplemental_repair_contract",),
                external_inputs=("ledger",),
                external_outputs=("rows", "unresolved"),
                state_reads=("supplemental_repair_contracts", "route_nodes", "validation_evidence", "reviews", "flowguard_work_orders"),
            ),
            _contract(
                "terminal.runtime.supplemental_repair_exhaustion",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_record_terminal_supplemental_repair_exhausted",
                implements=("terminal.supplemental_repair_contract",),
                external_inputs=("ledger", "blocker", "result"),
                external_outputs=("terminal_lifecycle"),
                state_reads=("terminal_supplemental_repair", "active_blockers"),
                state_writes=("terminal_supplemental_repair", "terminal_lifecycle"),
            ),
            _contract(
                "terminal.runtime.router_final_ready_current_packet_priority",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="router_next_action",
                implements=("terminal.final_quality_current_evidence_gates", "terminal.runtime_hard_gate_escape_return_path"),
                external_inputs=("ledger",),
                external_outputs=("RuntimeAction",),
                state_reads=("packets", "execution_frontier", "closure", "terminal_backward_replays"),
            ),
            _contract(
                "terminal.runtime.node_entry_gate_missing_reason",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_node_entry_gate_missing_reason",
                implements=("terminal.runtime_hard_gate_escape_return_path",),
                external_inputs=("ledger", "node_id"),
                external_outputs=("missing_reason"),
                state_reads=("route_nodes", "node_acceptance_plans", "node_context_packages"),
            ),
            _contract(
                "terminal.runtime.control_plane_hard_gate_escape_return_action",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_control_plane_hard_gate_escape_return_action",
                implements=("terminal.runtime_hard_gate_escape_return_path",),
                external_inputs=("ledger",),
                external_outputs=("RuntimeAction"),
                state_reads=("final_route_wide_gate_ledger", "route_nodes", "execution_frontier", "packets"),
            ),
            _contract(
                "terminal.runtime.closure_blockers",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_closure_blockers",
                implements=("terminal.final_quality_current_evidence_gates",),
                external_inputs=("ledger", "validation_evidence_id", "required_flowguard_target"),
                external_outputs=("blockers"),
                state_reads=("final_route_wide_gate_ledger", "final_requirement_evidence_matrix", "terminal_backward_replays"),
            ),
        ),
        test_evidence=(
            _evidence(
                "terminal.happy.replay_segments",
                test_name="test_terminal_replay_requires_reviewed_segments_and_pm_segment_decisions",
                path="tests/router_runtime/terminal.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_terminal",
                test_kind=HAPPY,
                covers=("terminal.final_ledger_and_backward_replay",),
            ),
            _evidence(
                "terminal.negative.final_ledger_sources",
                test_name="test_final_ledger_rejects_missing_source_of_truth_entries_and_contract_replay",
                path="tests/router_runtime/terminal.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_terminal",
                test_kind=NEGATIVE,
                covers=("terminal.final_ledger_and_backward_replay",),
            ),
            _evidence(
                "closure.failure.dirty_defect_ledger",
                test_name="test_terminal_closure_blocks_dirty_defect_ledger_after_terminal_replay",
                path="tests/router_runtime/closure.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_closure",
                test_kind=FAILURE,
                covers=("closure.dirty_ledgers_block_completion",),
            ),
            _evidence(
                "terminal.happy.final_quality_current_evidence",
                test_name="test_closure_accepted_evidence_projection_keeps_accepted_node_packets",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_closure_accepted_evidence_projection_keeps_accepted_node_packets",
                test_kind=HAPPY,
                covers=("terminal.final_quality_current_evidence_gates",),
                code_contracts=(
                    "terminal.runtime.review_evidence_current_and_accepted",
                    "terminal.runtime.flowguard_order_current_and_passing",
                    "terminal.runtime.validation_evidence_current_and_passing",
                    "terminal.runtime.final_requirement_evidence_matrix",
                    "terminal.runtime.closure_blockers",
                ),
            ),
            _evidence(
                "terminal.negative.final_quality_blocked_review",
                test_name="test_final_matrix_rejects_blocked_review_evidence_id",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_final_matrix_rejects_blocked_review_evidence_id",
                test_kind=NEGATIVE,
                covers=("terminal.final_quality_current_evidence_gates",),
                code_contracts=("terminal.runtime.review_evidence_current_and_accepted", "terminal.runtime.final_requirement_evidence_matrix", "terminal.runtime.closure_blockers"),
            ),
            _evidence(
                "terminal.negative.final_quality_stale_flowguard",
                test_name="test_final_matrix_rejects_stale_flowguard_evidence_id",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_final_matrix_rejects_stale_flowguard_evidence_id",
                test_kind=NEGATIVE,
                covers=("terminal.final_quality_current_evidence_gates",),
                code_contracts=("terminal.runtime.flowguard_order_current_and_passing", "terminal.runtime.final_requirement_evidence_matrix", "terminal.runtime.closure_blockers"),
            ),
            _evidence(
                "terminal.negative.final_quality_failed_validation",
                test_name="test_final_matrix_rejects_failed_validation_evidence_id",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_final_matrix_rejects_failed_validation_evidence_id",
                test_kind=NEGATIVE,
                covers=("terminal.final_quality_current_evidence_gates",),
                code_contracts=("terminal.runtime.validation_evidence_current_and_passing", "terminal.runtime.final_requirement_evidence_matrix", "terminal.runtime.closure_blockers"),
            ),
            _evidence(
                "terminal.negative.final_quality_old_route",
                test_name="test_final_matrix_ignores_old_route_evidence",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_final_matrix_ignores_old_route_evidence",
                test_kind=NEGATIVE,
                covers=("terminal.final_quality_current_evidence_gates",),
                code_contracts=("terminal.runtime.final_requirement_evidence_matrix",),
            ),
            _evidence(
                "terminal.replay.runtime_hard_gate_escape_matrix",
                test_name="test_final_hard_gate_escape_matrix_returns_each_runtime_gate_to_owner",
                path="tests/test_flowpilot_parent_entry_return_path.py",
                command="python -m unittest tests.test_flowpilot_parent_entry_return_path.FlowPilotParentEntryReturnPathTests.test_final_hard_gate_escape_matrix_returns_each_runtime_gate_to_owner",
                test_kind=REPLAY,
                covers=("terminal.runtime_hard_gate_escape_return_path",),
                code_contracts=(
                    "terminal.runtime.router_final_ready_current_packet_priority",
                    "terminal.runtime.control_plane_hard_gate_escape_return_action",
                    "terminal.runtime.node_entry_gate_missing_reason",
                ),
            ),
            _evidence(
                "terminal.negative.parent_child_entry_order",
                test_name="test_frontier_enters_next_parent_plan_before_child_after_prior_node_acceptance",
                path="tests/test_flowpilot_parent_entry_return_path.py",
                command="python -m unittest tests.test_flowpilot_parent_entry_return_path.FlowPilotParentEntryReturnPathTests.test_frontier_enters_next_parent_plan_before_child_after_prior_node_acceptance",
                test_kind=NEGATIVE,
                covers=("terminal.runtime_hard_gate_escape_return_path",),
                code_contracts=("terminal.runtime.node_entry_gate_missing_reason",),
            ),
            _evidence(
                "terminal.happy.final_quality_review_after_hard_gates_clean",
                test_name="test_final_quality_review_reachable_only_after_runtime_hard_gates_clean",
                path="tests/test_flowpilot_parent_entry_return_path.py",
                command="python -m unittest tests.test_flowpilot_parent_entry_return_path.FlowPilotParentEntryReturnPathTests.test_final_quality_review_reachable_only_after_runtime_hard_gates_clean",
                test_kind=HAPPY,
                covers=("terminal.runtime_hard_gate_escape_return_path",),
                code_contracts=("terminal.runtime.router_final_ready_current_packet_priority",),
            ),
            _evidence(
                "terminal.negative.terminal_replay_segment_parity",
                test_name="test_terminal_replay_rejects_missing_or_unexpected_segments",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_terminal_replay_rejects_missing_or_unexpected_segments",
                test_kind=NEGATIVE,
                covers=("terminal.final_quality_current_evidence_gates",),
                code_contracts=("terminal.runtime.terminal_backward_replay_result_contract",),
            ),
            _evidence(
                "terminal.negative.terminal_replay_semantic_blocker",
                test_name="test_terminal_replay_valid_block_records_semantic_blocker_not_mechanical_reissue",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_terminal_replay_valid_block_records_semantic_blocker_not_mechanical_reissue",
                test_kind=NEGATIVE,
                covers=("terminal.final_quality_current_evidence_gates",),
                code_contracts=(
                    "terminal.runtime.terminal_backward_replay_result_contract",
                    "terminal.runtime.closure_blockers",
                ),
            ),
            _evidence(
                "terminal.negative.terminal_replay_repair_loop",
                test_name="test_terminal_replay_repair_current_scope_preserves_targets_and_closes",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_terminal_replay_repair_current_scope_preserves_targets_and_closes",
                test_kind=NEGATIVE,
                covers=("terminal.final_quality_current_evidence_gates", "terminal.supplemental_repair_contract"),
                code_contracts=(
                    "terminal.runtime.terminal_backward_replay_result_contract",
                    "terminal.runtime.terminal_replay_current_scope_repair_packet",
                    "terminal.runtime.parse_supplemental_repair_contract",
                    "terminal.runtime.record_supplemental_repair_contract",
                    "terminal.runtime.supplemental_repair_closure_rows",
                    "terminal.runtime.router_final_ready_current_packet_priority",
                    "terminal.runtime.closure_blockers",
                ),
            ),
            _evidence(
                "terminal.negative.supplemental_contract_required",
                test_name="test_terminal_pm_repair_for_terminal_gap_requires_supplemental_contract",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_terminal_pm_repair_for_terminal_gap_requires_supplemental_contract",
                test_kind=NEGATIVE,
                covers=("terminal.supplemental_repair_contract",),
                code_contracts=("terminal.runtime.parse_supplemental_repair_contract",),
            ),
            _evidence(
                "terminal.negative.supplemental_projection_blocks_ledgers",
                test_name="test_supplemental_repair_item_projection_blocks_final_ledgers",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_supplemental_repair_item_projection_blocks_final_ledgers",
                test_kind=NEGATIVE,
                covers=("terminal.supplemental_repair_contract",),
                code_contracts=(
                    "terminal.runtime.supplemental_repair_closure_rows",
                    "terminal.runtime.final_requirement_evidence_matrix",
                    "terminal.runtime.closure_blockers",
                ),
            ),
            _evidence(
                "terminal.negative.supplemental_rounds_exhausted",
                test_name="test_terminal_supplemental_repair_exhausts_after_third_round_without_pm_packet",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m unittest tests.test_flowpilot_core_runtime.FlowPilotCoreRuntimeTests.test_terminal_supplemental_repair_exhausts_after_third_round_without_pm_packet",
                test_kind=NEGATIVE,
                covers=("terminal.supplemental_repair_contract",),
                code_contracts=("terminal.runtime.supplemental_repair_exhaustion",),
            ),
            _evidence(
                "terminal.happy.supplemental_repair_model",
                test_name="run_flowpilot_terminal_supplemental_repair_checks",
                path="simulations/run_flowpilot_terminal_supplemental_repair_checks.py",
                command="python simulations/run_flowpilot_terminal_supplemental_repair_checks.py",
                test_kind=HAPPY,
                covers=("terminal.supplemental_repair_contract",),
                code_contracts=(
                    "terminal.runtime.parse_supplemental_repair_contract",
                    "terminal.runtime.record_supplemental_repair_contract",
                    "terminal.runtime.supplemental_repair_closure_rows",
                    "terminal.runtime.supplemental_repair_exhaustion",
                ),
            ),
            _evidence(
                "terminal.negative.fake_e2e_terminal_replay_blocker",
                test_name="test_fake_end_to_end_terminal_replay_blocker_records_semantic_blocker",
                path="tests/test_flowpilot_new_entrypoint.py",
                command="python -m unittest tests.test_flowpilot_new_entrypoint.FlowPilotNewEntrypointTests.test_fake_end_to_end_terminal_replay_blocker_records_semantic_blocker",
                test_kind=NEGATIVE,
                covers=("terminal.final_quality_current_evidence_gates",),
            ),
            _evidence(
                "terminal.negative.fake_e2e_terminal_replay_repair_loop",
                test_name="test_fake_end_to_end_terminal_replay_blocker_repairs_to_completion",
                path="tests/test_flowpilot_new_entrypoint.py",
                command="python -m unittest tests.test_flowpilot_new_entrypoint.FlowPilotNewEntrypointTests.test_fake_end_to_end_terminal_replay_blocker_repairs_to_completion",
                test_kind=NEGATIVE,
                covers=("terminal.final_quality_current_evidence_gates",),
                code_contracts=(
                    "terminal.runtime.terminal_backward_replay_result_contract",
                    "terminal.runtime.terminal_replay_current_scope_repair_packet",
                    "terminal.runtime.router_final_ready_current_packet_priority",
                    "terminal.runtime.closure_blockers",
                ),
            ),
            _evidence(
                "resume.happy.loads_state",
                test_name="test_resume_reentry_loads_state_before_resume_cards",
                path="tests/router_runtime/resume.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_resume",
                test_kind=HAPPY,
                covers=("resume.current_run_reentry",),
            ),
            _evidence(
                "resume.failure.ambiguous_state",
                test_name="test_resume_ambiguous_state_blocks_continue_without_recovery_evidence",
                path="tests/router_runtime/resume.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_resume",
                test_kind=FAILURE,
                covers=("resume.current_run_reentry",),
            ),
        ),
    )

    role_output = ModelTestAlignmentPlan(
        model_id="role_output_contracts",
        obligations=(
            _obligation(
                "role_output.registry_authority",
                obligation_type="contract",
                description="Role outputs are registry-bound, role-authored, authority-checked, and submitted only through current Router waits.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "output_contract.packet_binding",
                obligation_type="contract",
                description="Output contracts are repeated in packet envelope/body/ledger/result and rejected for wrong recipients.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "output_contract.self_check_required_fields",
                obligation_type="hazard",
                description="Role-output self-checks expose exact missing required fields and do not treat a heading or wrong field name as a completed worker contract.",
                required_test_kinds=(NEGATIVE,),
            ),
        ),
        test_evidence=(
            _evidence(
                "role_output.happy.registry_preparable",
                test_name="test_registry_backed_output_types_are_preparable",
                path="tests/test_flowpilot_role_output_runtime.py",
                command="python -m unittest tests.test_flowpilot_role_output_runtime",
                test_kind=HAPPY,
                covers=("role_output.registry_authority",),
            ),
            _evidence(
                "role_output.negative.wrong_role",
                test_name="test_runtime_rejects_wrong_role_and_role_key_agent_id",
                path="tests/test_flowpilot_role_output_runtime.py",
                command="python -m unittest tests.test_flowpilot_role_output_runtime",
                test_kind=NEGATIVE,
                covers=("role_output.registry_authority",),
            ),
            _evidence(
                "output_contract.happy.packet_binding",
                test_name="test_pm_packet_repeats_output_contract_in_envelope_body_ledger_and_result",
                path="tests/test_flowpilot_output_contracts.py",
                command="python -m unittest tests.test_flowpilot_output_contracts",
                test_kind=HAPPY,
                covers=("output_contract.packet_binding",),
            ),
            _evidence(
                "output_contract.negative.wrong_recipient",
                test_name="test_packet_rejects_contract_for_wrong_recipient",
                path="tests/test_flowpilot_output_contracts.py",
                command="python -m unittest tests.test_flowpilot_output_contracts",
                test_kind=NEGATIVE,
                covers=("output_contract.packet_binding",),
            ),
            _evidence(
                "output_contract.negative.current_node_worker_missing_fields",
                test_name="test_contract_self_check_metadata_reports_current_node_worker_missing_fields",
                path="tests/test_flowpilot_output_contracts.py",
                command="python -m unittest tests.test_flowpilot_output_contracts",
                test_kind=NEGATIVE,
                covers=("output_contract.self_check_required_fields",),
            ),
        ),
    )

    router_loop_daemon = ModelTestAlignmentPlan(
        model_id="router_loop_daemon",
        obligations=(
            _obligation(
                "router_loop.packet_result_review_loop",
                obligation_type="transition",
                description="The current-node loop dispatches packets only after direct-dispatch preflight and routes results through PM/reviewer gates.",
                required_test_kinds=(HAPPY, FAILURE),
            ),
            _obligation(
                "router_loop.e2e_synthetic_chaos_replay",
                obligation_type="scenario",
                description="Daemon-driven fake AI replays cross startup, packet dispatch, repair, proof, parallel-run isolation, and terminal closure without treating bad packages as completion.",
                required_test_kinds=(HAPPY, FAILURE, EDGE),
            ),
            _obligation(
                "router_loop.real_router_dry_run_rehearsal",
                obligation_type="scenario",
                description="Prepared fake AI work packages exercise the real Router CLI/runtime, card ACK, packet active-holder, role-output, resume, proof, and terminal lifecycle boundaries before coverage is claimed.",
                required_test_kinds=(HAPPY, EDGE, NEGATIVE),
            ),
            _obligation(
                "router_loop.real_router_cli_boundary",
                obligation_type="contract",
                description="The public Router CLI can start, inspect, advance, apply, and record prepared role-output events without bypassing runtime payload requirements.",
                required_test_kinds=(HAPPY,),
            ),
            _obligation(
                "router_loop.control_plane_failure_canary",
                obligation_type="hazard",
                description="Bounded control-plane canaries cover locks, corrupt runtime persistence, daemon liveness, duplicate resume wakes, peer-run authority, terminal fences, and background proof artifacts.",
                required_test_kinds=(HAPPY, FAILURE, EDGE),
            ),
            _obligation(
                "router_loop.shadow_launcher_chaos_regression",
                obligation_type="scenario",
                description="Shadow launcher chaos regressions drive fake AI packages through an installed launcher copy, real Router/daemon state, recovery, peer isolation, current-pointer loading, malformed package rejection, and bounded cleanup loops.",
                required_test_kinds=(HAPPY, EDGE, NEGATIVE),
            ),
            _obligation(
                "router_loop.historical_live_run_replay_package_suite",
                obligation_type="scenario",
                description="Historical live-run replay packages bind prior real failure shapes to real Router, packet/runtime, resume, background proof, install, route evidence, display projection, and filesystem gates without claiming arbitrary live AI semantic quality.",
                required_test_kinds=(HAPPY, EDGE, NEGATIVE),
            ),
            _obligation(
                "router_loop.known_friction_regression_gate",
                obligation_type="hazard",
                description="The six accepted historical friction surfaces are pinned to current runtime-backed regressions and reject model-only, stale, progress-only, or skipped evidence overclaims.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "router_loop.package_disposition_repair_owned_role_output_replay",
                obligation_type="hazard",
                description="PM package-disposition conflict replay from role-output storage is classified as repair-owned audit evidence across material, research, and current-node paths instead of becoming a fresh disposition.",
                required_test_kinds=(EDGE, NEGATIVE),
            ),
            _obligation(
                "router_loop.package_disposition_repair_owned_daemon_replay",
                obligation_type="hazard",
                description="Daemon tick replay of repair-owned package-disposition conflicts quarantines stale evidence, preserves the legal owner wait, and does not enter daemon_error.",
                required_test_kinds=(EDGE, NEGATIVE),
            ),
            _obligation(
                "router_loop.package_disposition_stale_unowned_role_output_replay",
                obligation_type="hazard",
                description="Role-output replay of an older unowned package-disposition body is quarantined when a newer canonical package body already owns the same semantic identity.",
                required_test_kinds=(EDGE, NEGATIVE),
            ),
            _obligation(
                "router_loop.package_disposition_stale_unowned_daemon_replay",
                obligation_type="hazard",
                description="Daemon tick replay of an older unowned package-disposition body preserves the canonical body and does not enter daemon_error.",
                required_test_kinds=(EDGE, NEGATIVE),
            ),
            _obligation(
                "daemon.lock_status_and_queue_progress",
                obligation_type="invariant",
                description="The persistent Router daemon owns one run lock, records status, waits on fresh locks, and does not reactivate released locks.",
                required_test_kinds=(HAPPY, EDGE),
            ),
            _obligation(
                "daemon.parent_child_mesh",
                obligation_type="contract",
                description="Parent hierarchy consumes thin daemon child evidence for startup/lock, Controller actions, waits/liveness, and terminal/projection while retaining the layered full daemon model.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
        ),
        test_evidence=(
            _evidence(
                "router_loop.happy.direct_dispatch",
                test_name="test_current_node_packet_relay_uses_router_direct_dispatch",
                path="tests/router_runtime/packets.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_packets",
                test_kind=HAPPY,
                covers=("router_loop.packet_result_review_loop",),
            ),
            _evidence(
                "router_loop.failure.reviewer_audit",
                test_name="test_current_node_completion_requires_reviewer_passed_packet_audit",
                path="tests/router_runtime/packets.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_packets",
                test_kind=FAILURE,
                covers=("router_loop.packet_result_review_loop",),
            ),
            _evidence(
                "router_loop.e2e.happy.startup_to_terminal",
                test_name="test_e2e_golden_fake_ai_run_reaches_clean_terminal_lifecycle",
                path="tests/test_flowpilot_e2e_synthetic_chaos_replay.py",
                command="python -m pytest tests/test_flowpilot_e2e_synthetic_chaos_replay.py",
                test_kind=HAPPY,
                covers=("router_loop.e2e_synthetic_chaos_replay",),
            ),
            _evidence(
                "router_loop.e2e.failure.worker_repair",
                test_name="test_e2e_worker_bad_package_then_repair_continues_to_terminal",
                path="tests/test_flowpilot_e2e_synthetic_chaos_replay.py",
                command="python -m pytest tests/test_flowpilot_e2e_synthetic_chaos_replay.py",
                test_kind=FAILURE,
                covers=("router_loop.e2e_synthetic_chaos_replay",),
            ),
            _evidence(
                "router_loop.e2e.edge.parallel_isolation",
                test_name="test_e2e_parallel_run_peer_stop_does_not_mutate_current_run",
                path="tests/test_flowpilot_e2e_synthetic_chaos_replay.py",
                command="python -m pytest tests/test_flowpilot_e2e_synthetic_chaos_replay.py",
                test_kind=EDGE,
                covers=("router_loop.e2e_synthetic_chaos_replay",),
            ),
            _evidence(
                "router_loop.real_router.happy.full_rehearsal",
                test_name="test_real_router_full_fake_ai_package_rehearsal_reaches_terminal_standard_state",
                path="tests/test_flowpilot_real_router_dry_run_rehearsal.py",
                command="python -m pytest tests/test_flowpilot_real_router_dry_run_rehearsal.py",
                test_kind=HAPPY,
                covers=("router_loop.real_router_dry_run_rehearsal",),
            ),
            _evidence(
                "router_loop.real_router.happy.cli_boundary",
                test_name="test_real_router_full_fake_ai_package_rehearsal_reaches_terminal_standard_state",
                path="tests/test_flowpilot_real_router_dry_run_rehearsal.py",
                command="python -m pytest tests/test_flowpilot_real_router_dry_run_rehearsal.py",
                test_kind=HAPPY,
                covers=("router_loop.real_router_cli_boundary",),
            ),
            _evidence(
                "router_loop.real_router.edge.resume_and_proof",
                test_name="test_recovery_rehearsal_resume_idempotency_and_background_proof_gate",
                path="tests/test_flowpilot_real_router_dry_run_rehearsal.py",
                command="python -m pytest tests/test_flowpilot_real_router_dry_run_rehearsal.py",
                test_kind=EDGE,
                covers=("router_loop.real_router_dry_run_rehearsal",),
            ),
            _evidence(
                "router_loop.real_router.negative.known_bad_matrix",
                test_name="test_known_bad_rows_are_rejected",
                path="tests/test_flowpilot_real_router_dry_run_rehearsal_matrix.py",
                command="python -m pytest tests/test_flowpilot_real_router_dry_run_rehearsal_matrix.py",
                test_kind=NEGATIVE,
                covers=("router_loop.real_router_dry_run_rehearsal",),
            ),
            _evidence(
                "router_loop.canary.happy.duplicate_resume",
                test_name="test_canary_duplicate_manual_resume_is_idempotent",
                path="tests/test_flowpilot_control_plane_failure_canary_replay.py",
                command="python -m pytest tests/test_flowpilot_control_plane_failure_canary_replay.py",
                test_kind=HAPPY,
                covers=("router_loop.control_plane_failure_canary",),
            ),
            _evidence(
                "router_loop.canary.failure.lock_and_corrupt_persistence",
                test_name="test_canary_corrupt_scheduler_ledger_marks_daemon_error_not_live",
                path="tests/test_flowpilot_control_plane_failure_canary_replay.py",
                command="python -m pytest tests/test_flowpilot_control_plane_failure_canary_replay.py",
                test_kind=FAILURE,
                covers=("router_loop.control_plane_failure_canary",),
            ),
            _evidence(
                "router_loop.canary.edge.peer_stop_and_proof_gate",
                test_name="test_canary_peer_run_stop_does_not_mutate_current_run",
                path="tests/test_flowpilot_control_plane_failure_canary_replay.py",
                command="python -m pytest tests/test_flowpilot_control_plane_failure_canary_replay.py",
                test_kind=EDGE,
                covers=("router_loop.control_plane_failure_canary",),
            ),
            _evidence(
                "router_loop.shadow_launcher.happy.installed_start",
                test_name="test_installed_launcher_shadow_start_reaches_releasable_standard_state",
                path="tests/test_flowpilot_shadow_launcher_chaos_replay.py",
                command="python -m pytest tests/test_flowpilot_shadow_launcher_chaos_replay.py",
                test_kind=HAPPY,
                covers=("router_loop.shadow_launcher_chaos_regression",),
            ),
            _evidence(
                "router_loop.shadow_launcher.edge.recovery_peer_soak",
                test_name="test_crash_recovery_bundle_handles_dead_daemon_duplicate_resume_and_progress_only_proof",
                path="tests/test_flowpilot_shadow_launcher_chaos_replay.py",
                command="python -m pytest tests/test_flowpilot_shadow_launcher_chaos_replay.py",
                test_kind=EDGE,
                covers=("router_loop.shadow_launcher_chaos_regression",),
            ),
            _evidence(
                "router_loop.shadow_launcher.negative.bad_packages",
                test_name="test_malformed_fake_ai_package_generator_rejects_finite_bad_classes",
                path="tests/test_flowpilot_shadow_launcher_chaos_replay.py",
                command="python -m pytest tests/test_flowpilot_shadow_launcher_chaos_replay.py",
                test_kind=NEGATIVE,
                covers=("router_loop.shadow_launcher_chaos_regression",),
            ),
            _evidence(
                "router_loop.historical_live_run.happy.package_matrix",
                test_name="test_historical_live_run_rows_cover_required_surfaces",
                path="tests/test_flowpilot_historical_live_run_replay_matrix.py",
                command="python -m pytest tests/test_flowpilot_historical_live_run_replay_matrix.py",
                test_kind=HAPPY,
                covers=("router_loop.historical_live_run_replay_package_suite",),
            ),
            _evidence(
                "router_loop.historical_live_run.edge.snapshot_background_lifecycle",
                test_name="test_historical_snapshot_and_background_packages_reject_stale_or_incomplete_evidence",
                path="tests/test_flowpilot_historical_live_run_replay.py",
                command="python -m pytest tests/test_flowpilot_historical_live_run_replay.py",
                test_kind=EDGE,
                covers=("router_loop.historical_live_run_replay_package_suite",),
            ),
            _evidence(
                "router_loop.historical_live_run.negative.relay_semantic_overclaim",
                test_name="test_relay_lifecycle_and_semantic_contract_packages_block_overclaims",
                path="tests/test_flowpilot_historical_live_run_replay.py",
                command="python -m pytest tests/test_flowpilot_historical_live_run_replay.py",
                test_kind=NEGATIVE,
                covers=("router_loop.historical_live_run_replay_package_suite",),
            ),
            _evidence(
                "router_loop.known_friction.happy.matrix",
                test_name="test_known_friction_rows_cover_required_historical_failures",
                path="tests/test_flowpilot_known_friction_regression_matrix.py",
                command="python -m unittest tests.test_flowpilot_known_friction_regression_matrix",
                test_kind=HAPPY,
                covers=("router_loop.known_friction_regression_gate",),
            ),
            _evidence(
                "router_loop.known_friction.negative.known_bad",
                test_name="test_known_bad_cases_are_rejected",
                path="tests/test_flowpilot_known_friction_regression_matrix.py",
                command="python -m unittest tests.test_flowpilot_known_friction_regression_matrix",
                test_kind=NEGATIVE,
                covers=("router_loop.known_friction_regression_gate",),
            ),
            _evidence(
                "router_loop.package_disposition_repair_owned_replay.edge.role_output",
                test_name="test_repair_owned_package_disposition_conflict_replay_is_quarantined_without_daemon_error",
                path="tests/test_flowpilot_role_output_reconciliation.py",
                command="python -m pytest tests/test_flowpilot_role_output_reconciliation.py -k package_disposition_conflict",
                test_kind=EDGE,
                covers=("router_loop.package_disposition_repair_owned_role_output_replay",),
            ),
            _evidence(
                "router_loop.package_disposition_repair_owned_replay.edge.daemon_tick",
                test_name="test_daemon_tick_quarantines_repair_owned_package_conflict_without_erasing_wait",
                path="tests/test_flowpilot_role_output_reconciliation.py",
                command="python -m pytest tests/test_flowpilot_role_output_reconciliation.py -k package_disposition_conflict",
                test_kind=EDGE,
                covers=("router_loop.package_disposition_repair_owned_daemon_replay",),
            ),
            _evidence(
                "router_loop.package_disposition_repair_owned_replay.negative.classifier",
                test_name="test_pm_package_disposition_conflict_classifier_marks_repair_owned_replay",
                path="tests/test_flowpilot_control_plane_contracts.py",
                command="python -m pytest tests/test_flowpilot_control_plane_contracts.py -k pm_package_disposition",
                test_kind=NEGATIVE,
                covers=(
                    "router_loop.package_disposition_repair_owned_role_output_replay",
                    "router_loop.package_disposition_repair_owned_daemon_replay",
                ),
            ),
            _evidence(
                "router_loop.package_disposition_stale_unowned_replay.edge.role_output",
                test_name="test_stale_unowned_package_disposition_replay_preserves_canonical_body",
                path="tests/test_flowpilot_role_output_reconciliation.py",
                command="python -m pytest tests/test_flowpilot_role_output_reconciliation.py -k stale_unowned_package_disposition",
                test_kind=EDGE,
                covers=("router_loop.package_disposition_stale_unowned_role_output_replay",),
            ),
            _evidence(
                "router_loop.package_disposition_stale_unowned_replay.edge.daemon_tick",
                test_name="test_daemon_tick_quarantines_stale_unowned_package_replay_without_reverting_body",
                path="tests/test_flowpilot_role_output_reconciliation.py",
                command="python -m pytest tests/test_flowpilot_role_output_reconciliation.py -k stale_unowned_package",
                test_kind=EDGE,
                covers=("router_loop.package_disposition_stale_unowned_daemon_replay",),
            ),
            _evidence(
                "router_loop.package_disposition_stale_unowned_replay.negative.reject_old_body",
                test_name="test_stale_unowned_package_disposition_replay_preserves_canonical_body",
                path="tests/test_flowpilot_role_output_reconciliation.py",
                command="python -m pytest tests/test_flowpilot_role_output_reconciliation.py -k stale_unowned_package_disposition",
                test_kind=NEGATIVE,
                covers=("router_loop.package_disposition_stale_unowned_role_output_replay",),
            ),
            _evidence(
                "router_loop.package_disposition_stale_unowned_replay.negative.no_daemon_error",
                test_name="test_daemon_tick_quarantines_stale_unowned_package_replay_without_reverting_body",
                path="tests/test_flowpilot_role_output_reconciliation.py",
                command="python -m pytest tests/test_flowpilot_role_output_reconciliation.py -k stale_unowned_package",
                test_kind=NEGATIVE,
                covers=("router_loop.package_disposition_stale_unowned_daemon_replay",),
            ),
            _evidence(
                "daemon.happy.formal_startup",
                test_name="test_formal_startup_starts_router_daemon_before_controller_core",
                path="tests/router_runtime/startup_bootstrap.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=HAPPY,
                covers=("daemon.lock_status_and_queue_progress",),
            ),
            _evidence(
                "daemon.edge.fresh_lock_wait",
                test_name="test_router_daemon_waits_on_fresh_scheduler_write_lock_before_error",
                path="tests/router_runtime/startup_daemon.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_startup_daemon",
                test_kind=EDGE,
                covers=("daemon.lock_status_and_queue_progress",),
            ),
            _evidence(
                "daemon.happy.thin_child_mesh",
                test_name="test_daemon_child_reports_are_thin_and_green",
                path="tests/test_flowpilot_daemon_child_mesh.py",
                command="python -m unittest tests.test_flowpilot_daemon_child_mesh",
                test_kind=HAPPY,
                covers=("daemon.parent_child_mesh",),
            ),
            _evidence(
                "daemon.negative.parent_no_longer_consumes_large_monolith_model",
                test_name="test_parent_ledger_consumes_split_daemon_children_not_large_monolith_model",
                path="tests/test_flowpilot_daemon_child_mesh.py",
                command="python -m unittest tests.test_flowpilot_daemon_child_mesh",
                test_kind=NEGATIVE,
                covers=("daemon.parent_child_mesh",),
            ),
        ),
    )

    repair_transactions = ModelTestAlignmentPlan(
        model_id="repair_transactions",
        obligations=(
            _obligation(
                "repair_transactions.executable_plan_required",
                obligation_type="invariant",
                description="A committed PM repair transaction has a concrete queued action, existing producer, Router handler, or terminal stop.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "repair_transactions.current_repair_requires_concrete_producer",
                obligation_type="hazard",
                description="Current repair cannot commit a role reissue or existing-event wait without a concrete producer, and retired replacement-packet authority is not accepted.",
                required_test_kinds=(NEGATIVE,),
            ),
            _obligation(
                "repair_transactions.unsupported_event_replay_rejected",
                obligation_type="hazard",
                description="A repair transaction cannot use the unsupported event_replay plan kind; current repair plans need a registered producer/action/handler/terminal stop.",
                required_test_kinds=(NEGATIVE,),
            ),
            _obligation(
                "repair_transactions.empty_transaction_returns_to_pm_repair",
                obligation_type="contract",
                description="An empty delivered repair transaction returns to the PM repair-decision wait instead of being counted as executable repair work.",
                required_test_kinds=(NEGATIVE,),
            ),
            _obligation(
                "repair_transactions.pm_decision_flag_atomicity",
                obligation_type="hazard",
                description="A PM repair decision makes its required flag visible before daemon-readable post-decision wait events are exposed.",
                required_test_kinds=(EDGE,),
            ),
            _obligation(
                "repair_transactions.no_producer_rejection_then_current_recovery",
                obligation_type="scenario",
                description="Runtime rejects a producerless repair and converges after correction through a registered rerun target or safe operation replay.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "repair_transactions.route_mutation_supersedes_open_repair_blocker",
                obligation_type="hazard",
                description="Route mutation that quarantines an open repair packet records a terminal disposition on the prior repair-open blocker instead of leaving it active for final closure.",
                required_test_kinds=(EDGE,),
            ),
            _obligation(
                "repair_transactions.repair_loop_break_glass_threshold",
                obligation_type="hazard",
                description="A same-dossier same-parent consecutive repair loop may use ordinary PM repair through four repair nodes, but the fifth consecutive repair node without normal business recovery projects Controller break-glass duty and supersedes same-dossier PM repair packets instead of issuing another ordinary PM repair decision.",
                required_test_kinds=(HAPPY, NEGATIVE, EDGE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "repair_transactions.repair_loop_cross_node_non_trigger",
                obligation_type="hazard",
                description="Similar blocker problems across different route nodes stay in ordinary PM repair and do not trigger the same-node break-glass threshold by themselves.",
                required_test_kinds=(NEGATIVE,),
                allow_shared_implementation=True,
            ),
            _obligation(
                "repair_transactions.repair_loop_blocker_class_does_not_reset",
                obligation_type="hazard",
                description="A different blocker class in the same repair dossier does not reset the consecutive same-parent repair-loop count.",
                required_test_kinds=(EDGE,),
                allow_shared_implementation=True,
            ),
        ),
        code_contracts=(
            _contract(
                "repair_transactions.runtime.repair_loop_review",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_repair_loop_break_glass_review",
                implements=(
                    "repair_transactions.repair_loop_break_glass_threshold",
                    "repair_transactions.repair_loop_cross_node_non_trigger",
                    "repair_transactions.repair_loop_blocker_class_does_not_reset",
                ),
                external_inputs=("ledger", "blocker"),
                state_reads=("active_blockers", "packets"),
            ),
            _contract(
                "repair_transactions.runtime.pm_packet_threshold_gate",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_ensure_pm_repair_decision_packet_for_blocker",
                implements=("repair_transactions.repair_loop_break_glass_threshold",),
                external_inputs=("ledger", "blocker_id"),
                state_reads=("active_blockers", "packets"),
                state_writes=("active_blockers", "packets"),
                side_effects=("repair_loop_break_glass_required", "repair_loop_pm_repair_packets_superseded"),
            ),
            _contract(
                "repair_transactions.runtime.break_glass_next_action",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_repair_loop_break_glass_action",
                implements=("repair_transactions.repair_loop_break_glass_threshold",),
                external_inputs=("ledger",),
                state_reads=("active_blockers", "packets"),
            ),
            _contract(
                "repair_transactions.runtime.break_glass_foreground_duty",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="preview_foreground_duty",
                implements=("repair_transactions.repair_loop_break_glass_threshold",),
                external_inputs=("ledger", "guard"),
                state_reads=("lifecycle_guard", "foreground_duty"),
            ),
        ),
        test_evidence=(
            _evidence(
                "repair_transactions.happy.current_operation_replay",
                test_name="test_operation_replay_repair_transaction_queues_replay_action",
                path="tests/router_runtime/control_blockers.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_control_blockers",
                test_kind=HAPPY,
                covers=(
                    "repair_transactions.executable_plan_required",
                    "repair_transactions.no_producer_rejection_then_current_recovery",
                ),
            ),
            _evidence(
                "repair_transactions.negative.unsupported_event_replay_plan_kind",
                test_name="test_pm_repair_decision_rejects_unsupported_event_replay_plan_kind",
                path="tests/router_runtime/control_blockers.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_control_blockers",
                test_kind=NEGATIVE,
                covers=("repair_transactions.unsupported_event_replay_rejected",),
            ),
            _evidence(
                "repair_transactions.negative.empty_followup_wait_requires_pm_decision",
                test_name="test_delivered_control_blocker_with_empty_repair_transaction_requires_pm_repair_decision",
                path="tests/router_runtime/control_blockers.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_control_blockers",
                test_kind=NEGATIVE,
                covers=(
                    "repair_transactions.executable_plan_required",
                    "repair_transactions.empty_transaction_returns_to_pm_repair",
                    "repair_transactions.current_repair_requires_concrete_producer",
                    "repair_transactions.no_producer_rejection_then_current_recovery",
                ),
            ),
            _evidence(
                "repair_transactions.edge.pm_decision_side_effect_atomicity",
                test_name="test_pm_repair_decision_state_persists_before_followup_wait_is_exposed",
                path="tests/router_runtime/control_blockers.py",
                command="python -m unittest tests.test_flowpilot_router_runtime_control_blockers",
                test_kind=EDGE,
                covers=("repair_transactions.pm_decision_flag_atomicity",),
            ),
            _evidence(
                "repair_transactions.edge.route_mutation_supersedes_repair_open_blocker",
                test_name="test_route_mutation_supersedes_repair_open_blocker_for_quarantined_packet",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_route_mutation_supersedes_repair_open_blocker_for_quarantined_packet -q",
                test_kind=EDGE,
                covers=("repair_transactions.route_mutation_supersedes_open_repair_blocker",),
            ),
            _evidence(
                "repair_transactions.happy.repair_loop_fourth_allows_pm",
                test_name="test_break_glass_threshold_triggers_on_fifth_repair_blocker",
                path="tests/test_flowpilot_core_runtime.py",
                command="python -m pytest tests/test_flowpilot_core_runtime.py -k test_break_glass_threshold_triggers_on_fifth_repair_blocker -q",
                test_kind=HAPPY,
                covers=("repair_transactions.repair_loop_break_glass_threshold",),
                code_contracts=(
                    "repair_transactions.runtime.repair_loop_review",
                    "repair_transactions.runtime.pm_packet_threshold_gate",
                ),
            ),
            _evidence(
                "repair_transactions.negative.repair_loop_fifth_break_glass",
                test_name="test_fifth_repeated_blocker_projects_break_glass_instead_of_pm_repair",
                path="tests/test_flowpilot_complete_system_runtime.py",
                command="python -m pytest tests/test_flowpilot_complete_system_runtime.py -k test_fifth_repeated_blocker_projects_break_glass_instead_of_pm_repair -q",
                test_kind=NEGATIVE,
                covers=("repair_transactions.repair_loop_break_glass_threshold",),
                code_contracts=(
                    "repair_transactions.runtime.repair_loop_review",
                    "repair_transactions.runtime.pm_packet_threshold_gate",
                    "repair_transactions.runtime.break_glass_next_action",
                    "repair_transactions.runtime.break_glass_foreground_duty",
                ),
            ),
            _evidence(
                "repair_transactions.edge.repair_loop_normalized_route_family",
                test_name="test_repair_loop_family_count_normalizes_route_repair_versions",
                path="tests/test_flowpilot_complete_system_runtime.py",
                command="python -m pytest tests/test_flowpilot_complete_system_runtime.py -k test_repair_loop_family_count_normalizes_route_repair_versions -q",
                test_kind=EDGE,
                covers=("repair_transactions.repair_loop_break_glass_threshold",),
                code_contracts=("repair_transactions.runtime.repair_loop_review",),
            ),
            _evidence(
                "repair_transactions.negative.repair_loop_cross_node_no_break_glass",
                test_name="test_cross_node_similar_blockers_do_not_trigger_repair_loop_break_glass",
                path="tests/test_flowpilot_complete_system_runtime.py",
                command="python -m pytest tests/test_flowpilot_complete_system_runtime.py -k test_cross_node_similar_blockers_do_not_trigger_repair_loop_break_glass -q",
                test_kind=NEGATIVE,
                covers=("repair_transactions.repair_loop_cross_node_non_trigger",),
                code_contracts=("repair_transactions.runtime.repair_loop_review",),
            ),
            _evidence(
                "repair_transactions.edge.repair_loop_blocker_class_does_not_reset",
                test_name="test_same_node_loop_count_does_not_reset_after_different_blocker_class",
                path="tests/test_flowpilot_complete_system_runtime.py",
                command="python -m pytest tests/test_flowpilot_complete_system_runtime.py -k test_same_node_loop_count_does_not_reset_after_different_blocker_class -q",
                test_kind=EDGE,
                covers=("repair_transactions.repair_loop_blocker_class_does_not_reset",),
                code_contracts=("repair_transactions.runtime.repair_loop_review",),
            ),
            _evidence(
                "repair_transactions.negative.repair_loop_card_guidance",
                test_name="test_repair_loop_threshold_routes_to_break_glass_guidance",
                path="tests/test_flowpilot_card_instruction_coverage.py",
                command="python -m pytest tests/test_flowpilot_card_instruction_coverage.py -k test_repair_loop_threshold_routes_to_break_glass_guidance -q",
                test_kind=NEGATIVE,
                covers=("repair_transactions.repair_loop_break_glass_threshold",),
            ),
        ),
    )

    tiering = ModelTestAlignmentPlan(
        model_id="test_tiering_slow_contracts",
        obligations=(
            _obligation(
                "test_tiering.foreground_fast_scope",
                obligation_type="contract",
                description="Fast/router tiers are scoped, foreground-safe, and exclude release-only, coverage sweep, and full parent regressions.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "test_tiering.background_artifact_contract",
                obligation_type="hazard",
                description="Background validation needs final out/err/combined/exit/meta artifacts; progress lines alone are not pass evidence.",
                required_test_kinds=(NEGATIVE,),
            ),
            _obligation(
                "test_tiering.shared_runtime_resource_serialization",
                obligation_type="hazard",
                description="Background commands that launch the same installed shadow runtime declare one exclusive resource and cannot overlap, while unrelated model checks remain parallel.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "slow_test.parent_child_contracts",
                obligation_type="contract",
                description="Slow-test parents declare child owners and I/O contracts and do not replay child internals as parent proof.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "test_tiering.final_confidence_acyclic_terminal_consumer",
                obligation_type="invariant",
                description="All, formal-submit-adversarial, and release proof compile before strict MTA/TestMesh parents; repository final-confidence is a downstream terminal consumer and per-run terminal return remains run-local.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
        ),
        code_contracts=(
            _contract(
                "runtime_path.test_tiering_slow_contracts.test_tiering_shared_runtime_resource_serialization",
                path="scripts/test_tier/background_supervisor.py",
                symbol="next_background_launch_index",
                implements=("test_tiering.shared_runtime_resource_serialization",),
                external_inputs=("pending_tier_commands", "running_tier_commands"),
                external_outputs=("next_launch_index_or_wait",),
                state_reads=(
                    "background_stage",
                    "background_exclusive_resource",
                ),
                error_paths=("same_exclusive_resource_selected_while_owner_running",),
                behavior_plane="development_process",
                behavior_commitment_id="commit.testmesh_pass_requires_current_proof",
            ),
        ),
        test_evidence=(
            _evidence(
                "tiering.happy.fast_scope",
                test_name="test_fast_tier_excludes_release_coverage_and_full_regression",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers",
                test_kind=HAPPY,
                covers=("test_tiering.foreground_fast_scope",),
            ),
            _evidence(
                "tiering.negative.release_exclusion",
                test_name="test_fast_and_router_tiers_do_not_contain_release_only_commands",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers",
                test_kind=NEGATIVE,
                covers=("test_tiering.foreground_fast_scope",),
            ),
            _evidence(
                "tiering.negative.progress_only",
                test_name="test_tiering_flowguard_model_rejects_known_bad_hazards",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers.FlowPilotTestTierTests.test_tiering_flowguard_model_rejects_known_bad_hazards",
                test_kind=NEGATIVE,
                covers=("test_tiering.background_artifact_contract",),
            ),
            _evidence(
                "tiering.happy.shared_runtime_resource_serialization",
                test_name="test_background_supervisor_serializes_shared_runtime_resources",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers.FlowPilotTestTierTests.test_background_supervisor_serializes_shared_runtime_resources",
                test_kind=HAPPY,
                covers=("test_tiering.shared_runtime_resource_serialization",),
                code_contracts=("runtime_path.test_tiering_slow_contracts.test_tiering_shared_runtime_resource_serialization",),
            ),
            _evidence(
                "tiering.negative.shared_runtime_resource_race",
                test_name="test_tiering_flowguard_model_rejects_known_bad_hazards",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers.FlowPilotTestTierTests.test_tiering_flowguard_model_rejects_known_bad_hazards",
                test_kind=NEGATIVE,
                covers=("test_tiering.shared_runtime_resource_serialization",),
                code_contracts=("runtime_path.test_tiering_slow_contracts.test_tiering_shared_runtime_resource_serialization",),
            ),
            _evidence(
                "slow_contract.happy.valid_contracts",
                test_name="test_slow_test_contract_flowguard_model_rejects_parent_child_hazards",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers.FlowPilotTestTierTests.test_slow_test_contract_flowguard_model_rejects_parent_child_hazards",
                test_kind=HAPPY,
                covers=("slow_test.parent_child_contracts",),
            ),
            _evidence(
                "slow_contract.negative.parent_child_hazards",
                test_name="test_slow_test_contract_flowguard_model_rejects_parent_child_hazards",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers.FlowPilotTestTierTests.test_slow_test_contract_flowguard_model_rejects_parent_child_hazards",
                test_kind=NEGATIVE,
                covers=("slow_test.parent_child_contracts",),
            ),
            _evidence(
                "tiering.happy.acyclic_final_confidence_dependency",
                test_name="test_release_and_final_confidence_have_acyclic_single_owner_order",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers.FlowPilotTestTierTests.test_release_and_final_confidence_have_acyclic_single_owner_order",
                test_kind=HAPPY,
                covers=("test_tiering.final_confidence_acyclic_terminal_consumer",),
            ),
            _evidence(
                "tiering.negative.acyclic_final_confidence_dependency",
                test_name="test_tiering_flowguard_model_rejects_known_bad_hazards",
                path="tests/test_flowpilot_test_tiers.py",
                command="python -m unittest tests.test_flowpilot_test_tiers.FlowPilotTestTierTests.test_tiering_flowguard_model_rejects_known_bad_hazards",
                test_kind=NEGATIVE,
                covers=("test_tiering.final_confidence_acyclic_terminal_consumer",),
            ),
        ),
    )

    meta_capability = ModelTestAlignmentPlan(
        model_id="meta_capability_parents",
        obligations=(
            _obligation(
                "meta_parent.thin_default_and_layered_full_boundary",
                obligation_type="contract",
                description="Meta parent routine evidence uses thin-parent proof by default and layered full proof only when explicitly requested.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "capability_parent.proof_reuse_and_fast_boundary",
                obligation_type="contract",
                description="Capability parent evidence rejects stale proof reuse and keeps fast smoke on the current path.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "parents.abstract_not_ordinary_conformance",
                obligation_type="invariant",
                description="Meta/Capability parent model evidence stays bounded as abstract model-hierarchy confidence, not ordinary production conformance.",
                required_test_kinds=(EDGE,),
            ),
        ),
        test_evidence=(
            _evidence(
                "meta_parent.happy.thin_default",
                test_name="test_default_meta_runner_uses_thin_parent_without_full_graph",
                path="tests/test_flowpilot_thin_parent_checks.py",
                command="python -m unittest tests.test_flowpilot_thin_parent_checks",
                test_kind=HAPPY,
                covers=("meta_parent.thin_default_and_layered_full_boundary",),
            ),
            _evidence(
                "meta_parent.negative.layered_explicit_only",
                test_name="test_full_meta_runner_uses_layered_parent_without_full_graph",
                path="tests/test_flowpilot_thin_parent_checks.py",
                command="python -m unittest tests.test_flowpilot_thin_parent_checks",
                test_kind=NEGATIVE,
                covers=("meta_parent.thin_default_and_layered_full_boundary",),
            ),
            _evidence(
                "capability_parent.happy.proof_reuse_guard",
                test_name="test_capability_result_proof_rejects_stale_reuse",
                path="tests/test_flowguard_result_proof.py",
                command="python -m unittest tests.test_flowguard_result_proof",
                test_kind=HAPPY,
                covers=("capability_parent.proof_reuse_and_fast_boundary",),
            ),
            _evidence(
                "capability_parent.negative.fast_smoke_current_path",
                test_name="test_smoke_fast_only_marks_slow_model_checks_fast",
                path="tests/test_flowguard_result_proof.py",
                command="python -m unittest tests.test_flowguard_result_proof",
                test_kind=NEGATIVE,
                covers=("capability_parent.proof_reuse_and_fast_boundary",),
            ),
            _evidence(
                "parents.edge.control_gate_unit_checks",
                test_name="FlowPilotControlGateTests meta/capability invariant checks",
                path="tests/test_flowpilot_control_gates.py",
                command="python -m unittest tests.test_flowpilot_control_gates",
                test_kind=EDGE,
                covers=("parents.abstract_not_ordinary_conformance",),
            ),
        ),
    )

    rejection_liveness = ModelTestAlignmentPlan(
        model_id="flowpilot_rejection_liveness_matrix",
        obligations=(
            _obligation(
                "rejection_liveness.required_cell_ownership",
                obligation_type="contract",
                description="Every current-contract malformed-output family/defect cell has one test owner and no live-completion authority.",
                required_test_kinds=(HAPPY, NEGATIVE),
            ),
            _obligation(
                "rejection_liveness.no_delta_retry_feedback",
                obligation_type="hazard",
                description="No-delta fake-AI retries are treated as control-flow hazards unless the retry changes the missing field, body, owner, or legal repair shape.",
                required_test_kinds=(NEGATIVE, REPLAY),
            ),
            _obligation(
                "rejection_liveness.stuck_absorption",
                obligation_type="invariant",
                description="Once the lifecycle guard marks the same nonterminal action/event as stuck, later previews must keep it blocked until real progress changes the event count or action.",
                required_test_kinds=(NEGATIVE, EDGE),
            ),
            _obligation(
                "rejection_liveness.live_projection_blocks_repeated_action",
                obligation_type="hazard",
                description="Live current-run projection blocks repeated lifecycle actions that were not absorbed into control_plane_stuck.",
                required_test_kinds=(NEGATIVE, EDGE),
            ),
            _obligation(
                "rejection_liveness.synthetic_boundary",
                obligation_type="contract",
                description="Synthetic fake-AI rehearsals may prove control-flow behavior but cannot claim live semantic completion.",
                required_test_kinds=(EDGE,),
            ),
        ),
        test_evidence=(
            _evidence(
                "rejection_liveness.happy.model_matrix",
                test_name="run_flowpilot_rejection_liveness_matrix_checks",
                path="simulations/run_flowpilot_rejection_liveness_matrix_checks.py",
                command="python simulations/run_flowpilot_rejection_liveness_matrix_checks.py --json-out simulations/flowpilot_rejection_liveness_matrix_results.json",
                test_kind=HAPPY,
                covers=("rejection_liveness.required_cell_ownership",),
            ),
            _evidence(
                "rejection_liveness.negative.no_delta_model_matrix",
                test_name="run_flowpilot_rejection_liveness_matrix_checks",
                path="simulations/run_flowpilot_rejection_liveness_matrix_checks.py",
                command="python simulations/run_flowpilot_rejection_liveness_matrix_checks.py --json-out simulations/flowpilot_rejection_liveness_matrix_results.json",
                test_kind=NEGATIVE,
                covers=("rejection_liveness.no_delta_retry_feedback",),
            ),
            _evidence(
                "rejection_liveness.negative.required_cell_owners",
                test_name="test_rejection_liveness_required_cells_have_owners",
                path="tests/test_flowpilot_synthetic_agent_coverage_matrix.py",
                command="python -m unittest tests.test_flowpilot_synthetic_agent_coverage_matrix",
                test_kind=NEGATIVE,
                covers=("rejection_liveness.required_cell_ownership",),
            ),
            _evidence(
                "rejection_liveness.replay.no_delta_retry_matrix",
                test_name="test_rejection_liveness_fake_ai_matrix_covers_no_delta_and_corrected_retry",
                path="tests/test_flowpilot_synthetic_agent_trace_replay.py",
                command="python -m unittest tests.test_flowpilot_synthetic_agent_trace_replay.FlowPilotSyntheticAgentTraceReplayTests.test_rejection_liveness_fake_ai_matrix_covers_no_delta_and_corrected_retry",
                test_kind=REPLAY,
                covers=("rejection_liveness.no_delta_retry_feedback", "rejection_liveness.synthetic_boundary"),
            ),
            _evidence(
                "rejection_liveness.negative.stuck_absorption",
                test_name="test_prior_stuck_decision_absorbs_same_action_until_progress_event",
                path="tests/test_flowpilot_lifecycle_guard.py",
                command="python -m unittest tests.test_flowpilot_lifecycle_guard.FlowPilotLifecycleGuardTests.test_prior_stuck_decision_absorbs_same_action_until_progress_event",
                test_kind=NEGATIVE,
                covers=("rejection_liveness.stuck_absorption",),
            ),
            _evidence(
                "rejection_liveness.edge.stuck_absorption",
                test_name="test_patrol_does_not_classify_repeated_role_dispatch_as_stuck",
                path="tests/test_flowpilot_lifecycle_guard.py",
                command="python -m unittest tests.test_flowpilot_lifecycle_guard.FlowPilotLifecycleGuardTests.test_patrol_does_not_classify_repeated_role_dispatch_as_stuck",
                test_kind=EDGE,
                covers=("rejection_liveness.stuck_absorption",),
            ),
            _evidence(
                "rejection_liveness.negative.live_projection",
                test_name="test_process_liveness_projection_blocks_unabsorbed_repeated_lifecycle_action",
                path="tests/test_flowpilot_full_model_test_gap_closure.py",
                command="python -m unittest tests.test_flowpilot_full_model_test_gap_closure.FlowPilotFullModelTestGapClosureTests.test_process_liveness_projection_blocks_unabsorbed_repeated_lifecycle_action",
                test_kind=NEGATIVE,
                covers=("rejection_liveness.live_projection_blocks_repeated_action",),
            ),
            _evidence(
                "rejection_liveness.edge.synthetic_boundary",
                test_name="test_synthetic_rows_are_non_live_and_backed_by_trace_tests",
                path="tests/test_flowpilot_synthetic_agent_coverage_matrix.py",
                command="python -m unittest tests.test_flowpilot_synthetic_agent_coverage_matrix",
                test_kind=EDGE,
                covers=("rejection_liveness.synthetic_boundary",),
            ),
            _evidence(
                "rejection_liveness.edge.live_projection",
                test_name="test_process_liveness_projection_blocks_unabsorbed_repeated_lifecycle_action",
                path="tests/test_flowpilot_full_model_test_gap_closure.py",
                command="python -m unittest tests.test_flowpilot_full_model_test_gap_closure.FlowPilotFullModelTestGapClosureTests.test_process_liveness_projection_blocks_unabsorbed_repeated_lifecycle_action",
                test_kind=EDGE,
                covers=("rejection_liveness.live_projection_blocks_repeated_action",),
            ),
        ),
    )

    route_authority = ModelTestAlignmentPlan(
        model_id="flowpilot_route_authority_singularity",
        obligations=(
            _obligation(
                "route_authority.single_owner_and_legal_action_visibility",
                obligation_type="invariant",
                description="Every current route-action decision exposes the single current owner, legal action ids, forbidden action ids, and required repair command from the route action policy registry.",
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "route_authority.reject_wrong_path_alias_and_fallback",
                obligation_type="hazard",
                description="Wrong-path route actions, old event aliases, fallback/prose payload shapes, and role-overreach are rejected with structured route-authority feedback instead of being translated.",
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_implementation=True,
            ),
            _obligation(
                "route_authority.corrected_retry_changes_packet_shape",
                obligation_type="hazard",
                description="After a route-authority rejection, a corrected retry must use the named legal repair command and change the package shape; repeated no-delta submissions remain blocked.",
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_implementation=True,
            ),
            _obligation(
                "route_authority.parent_mesh_blocks_missing_or_conflicted_evidence",
                obligation_type="contract",
                description="ModelMesh treats missing route-authority model evidence, missing projection, owner conflicts, wrong-path acceptance, fallback acceptance, and no-delta repeat acceptance as blocking parent hazards.",
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_implementation=True,
            ),
            _obligation(
                "route_authority.fake_ai_variant_matrix",
                obligation_type="hazard",
                description="Fake-AI route-authority variants cover wrong role, old aliases, fallback/prose payloads, missing feedback fields, and repeated no-delta submissions as separate modeled hazards.",
                required_test_kinds=(REPLAY,),
                allow_shared_implementation=True,
            ),
        ),
        code_contracts=(
            _contract(
                "route_authority.runtime.snapshot",
                path="skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion.py",
                symbol="_route_authority_snapshot",
                implements=("route_authority.single_owner_and_legal_action_visibility",),
                external_inputs=("policy_by_id", "frontier", "active_node_kind", "legal_ids", "blocking_reasons"),
                external_outputs=("route_authority_snapshot",),
                state_reads=("execution_frontier", "route_action_policy_registry"),
                side_effects=("legal_next_action_context",),
                error_paths=("owner_missing", "owner_conflict"),
            ),
            _contract(
                "route_authority.runtime.require_legal_action",
                path="skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion.py",
                symbol="_require_legal_route_action",
                implements=(
                    "route_authority.single_owner_and_legal_action_visibility",
                    "route_authority.reject_wrong_path_alias_and_fallback",
                ),
                external_inputs=("action_id", "context"),
                state_reads=("execution_frontier", "route_action_policy_registry", "run_state.flags"),
                side_effects=("wrong_path_rejection",),
                error_paths=("wrong_path",),
            ),
            _contract(
                "route_authority.runtime.reject_submission",
                path="skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion.py",
                symbol="_reject_route_authority_submission",
                implements=(
                    "route_authority.reject_wrong_path_alias_and_fallback",
                    "route_authority.corrected_retry_changes_packet_shape",
                ),
                external_inputs=("rejected_action_id", "context", "rejected_event", "rejection_kind"),
                external_outputs=("RouterError", "control_blocker"),
                state_reads=("execution_frontier", "route_action_policy_registry"),
                state_writes=("active_control_blocker", "control_blocker_artifact"),
                side_effects=("route_authority_rejection_blocker",),
                error_paths=("wrong_path", "unsupported_event_alias", "unsupported_payload_shape"),
            ),
            _contract(
                "route_authority.runtime.reject_unsupported_payload",
                path="skills/flowpilot/assets/flowpilot_router_route_frontier_policy_completion.py",
                symbol="_reject_unsupported_route_authority_payload",
                implements=("route_authority.reject_wrong_path_alias_and_fallback",),
                external_inputs=("event", "action_id", "payload"),
                state_reads=("payload", "route_action_policy_registry"),
                state_writes=("active_control_blocker",),
                side_effects=("unsupported_payload_rejection",),
                error_paths=("unsupported_payload_shape",),
            ),
        ),
        test_evidence=(
            _evidence(
                "route_authority.happy.model_matrix",
                test_name="run_flowpilot_route_authority_singularity_checks",
                path="simulations/run_flowpilot_route_authority_singularity_checks.py",
                command="python simulations/run_flowpilot_route_authority_singularity_checks.py --json-out simulations/flowpilot_route_authority_singularity_results.json",
                test_kind=HAPPY,
                covers=(
                    "route_authority.single_owner_and_legal_action_visibility",
                    "route_authority.parent_mesh_blocks_missing_or_conflicted_evidence",
                ),
                code_contracts=("route_authority.runtime.snapshot",),
            ),
            _evidence(
                "route_authority.negative.model_matrix",
                test_name="run_flowpilot_route_authority_singularity_checks",
                path="simulations/run_flowpilot_route_authority_singularity_checks.py",
                command="python simulations/run_flowpilot_route_authority_singularity_checks.py --json-out simulations/flowpilot_route_authority_singularity_results.json",
                test_kind=NEGATIVE,
                covers=("route_authority.corrected_retry_changes_packet_shape",),
                code_contracts=(
                    "route_authority.runtime.snapshot",
                    "route_authority.runtime.reject_submission",
                    "route_authority.runtime.reject_unsupported_payload",
                ),
            ),
            _evidence(
                "route_authority.replay.fake_ai_matrix_variants",
                test_name="test_route_authority_fake_ai_matrix_covers_alias_fallback_no_delta_and_feedback",
                path="tests/test_flowpilot_synthetic_agent_trace_replay.py",
                command="python -m unittest tests.test_flowpilot_synthetic_agent_trace_replay.FlowPilotSyntheticAgentTraceReplayTests.test_route_authority_fake_ai_matrix_covers_alias_fallback_no_delta_and_feedback",
                test_kind=REPLAY,
                covers=("route_authority.fake_ai_variant_matrix",),
                code_contracts=(
                    "route_authority.runtime.snapshot",
                    "route_authority.runtime.reject_submission",
                    "route_authority.runtime.reject_unsupported_payload",
                ),
            ),
            _evidence(
                "route_authority.negative.runtime_rejections",
                test_name="RouteMutationParentBackwardRuntimeTests route-authority rejection tests",
                path="tests/router_runtime/route_mutation_parent_backward.py",
                command="python -m unittest tests.router_runtime.route_mutation_parent_backward.RouteMutationParentBackwardRuntimeTests",
                test_kind=NEGATIVE,
                covers=(
                    "route_authority.single_owner_and_legal_action_visibility",
                    "route_authority.reject_wrong_path_alias_and_fallback",
                ),
                code_contracts=(
                    "route_authority.runtime.require_legal_action",
                    "route_authority.runtime.reject_submission",
                    "route_authority.runtime.reject_unsupported_payload",
                ),
            ),
            _evidence(
                "route_authority.replay.corrected_retry",
                test_name="test_route_authority_wrong_path_rejection_guides_corrected_retry_fake_package",
                path="tests/test_flowpilot_synthetic_agent_trace_replay.py",
                command="python -m unittest tests.test_flowpilot_synthetic_agent_trace_replay.FlowPilotSyntheticExceptionTraceReplayTests.test_route_authority_wrong_path_rejection_guides_corrected_retry_fake_package",
                test_kind=REPLAY,
                covers=(
                    "route_authority.reject_wrong_path_alias_and_fallback",
                    "route_authority.corrected_retry_changes_packet_shape",
                ),
                code_contracts=(
                    "route_authority.runtime.require_legal_action",
                    "route_authority.runtime.reject_submission",
                ),
            ),
            _evidence(
                "route_authority.negative.model_mesh_parent",
                test_name="test_missing_or_failed_child_result_blocks_parent",
                path="tests/test_flowpilot_model_mesh_coverage_receipts.py",
                command="python -m pytest tests/test_flowpilot_model_mesh_coverage_receipts.py::FlowPilotModelMeshCoverageReceiptTests::test_missing_or_failed_child_result_blocks_parent -q",
                test_kind=NEGATIVE,
                covers=("route_authority.parent_mesh_blocks_missing_or_conflicted_evidence",),
            ),
        ),
    )

    core_deliverable = ModelTestAlignmentPlan(
        model_id="core_deliverable_non_downgrade",
        obligations=(
            _obligation(
                "core_deliverable.non_downgrade_prompt_and_replay",
                obligation_type="hazard",
                description=(
                    "PM, Reviewer, child-skill, and FlowGuard operator prompt surfaces plus "
                    "synthetic bad-chain replay reject reachable-only, status-only, report-only, "
                    "honest-missing, partial, external-only, not-yet-done, or weaker child-output "
                    "substitutes for the accepted deliverable."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
        ),
        test_evidence=(
            _evidence(
                "core_deliverable.negative.prompt_cards",
                test_name="test_prompt_first_quality_chain_preserves_source_intent_without_runtime_semantic_gate",
                path="tests/test_flowpilot_card_instruction_coverage.py",
                command=(
                    "python -m unittest tests.test_flowpilot_card_instruction_coverage."
                    "FlowPilotCardInstructionCoverageTests."
                    "test_prompt_first_quality_chain_preserves_source_intent_without_runtime_semantic_gate"
                ),
                test_kind=NEGATIVE,
                covers=("core_deliverable.non_downgrade_prompt_and_replay",),
            ),
            _evidence(
                "core_deliverable.replay.synthetic_downgrade_chain",
                test_name="test_core_deliverable_downgrade_chain_blocks_completion",
                path="tests/test_flowpilot_synthetic_agent_trace_replay.py",
                command=(
                    "python -m unittest tests.test_flowpilot_synthetic_agent_trace_replay."
                    "FlowPilotSyntheticAgentTraceReplayTests."
                    "test_core_deliverable_downgrade_chain_blocks_completion"
                ),
                test_kind=REPLAY,
                covers=("core_deliverable.non_downgrade_prompt_and_replay",),
            ),
        ),
    )

    flowguard_053_ppa_maintenance = ModelTestAlignmentPlan(
        model_id="flowpilot_053_ppa_maintenance",
        obligations=(
            _obligation(
                "flowpilot_053.primary_path_authority_no_fallback",
                obligation_type="primary_path_authority",
                description=(
                    "FlowPilot package/result/blocker repair behavior is registered "
                    "through FlowGuard 0.53 Primary Path Authority with one current "
                    "primary path per business intent and no old-field, alias, prose, "
                    "or helper fallback success."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "flowpilot_053.behavior_commitments_cover_current_contract_promises",
                obligation_type="behavior_commitment",
                description=(
                    "User-visible FlowPilot no-fallback, PM-visible summary, "
                    "authorized result read, and release evidence promises are "
                    "registered in the Behavior Commitment Ledger with current "
                    "evidence and PPA handoff."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "flowpilot_053.field_lifecycle_current_fields_no_compatibility",
                obligation_type="field_lifecycle",
                description=(
                    "Existing current fields pm_visible_summary, "
                    "recent_role_report_summary, and authorized_result_reads have "
                    "FieldLifecycle ownership and tests, while legacy summary fields "
                    "remain blocked rather than accepted through compatibility."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "flowpilot_053.release_evidence_consumes_upgrade_and_ppa",
                obligation_type="release_evidence",
                description=(
                    "Release or broad maintenance confidence consumes the 0.53 "
                    "project upgrade, PPA/BCL, FieldLifecycle, RiskEvidence, MTA, "
                    "synthetic fake-agent coverage, topology, and install-sync "
                    "evidence instead of treating routine green evidence as release proof."
                ),
                required_test_kinds=(HAPPY, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
        ),
        code_contracts=(
            _contract(
                "flowpilot_053.runner.build_report",
                path="simulations/run_flowpilot_053_ppa_maintenance_checks.py",
                symbol="build_report",
                implements=(
                    "flowpilot_053.primary_path_authority_no_fallback",
                    "flowpilot_053.behavior_commitments_cover_current_contract_promises",
                    "flowpilot_053.field_lifecycle_current_fields_no_compatibility",
                    "flowpilot_053.release_evidence_consumes_upgrade_and_ppa",
                ),
                external_inputs=("FlowGuard 0.53 PPA/BCL/FieldLifecycle/RiskEvidence plans",),
                external_outputs=("green report or blocked findings",),
                error_paths=("negative case expected codes missing",),
            ),
            _contract(
                "flowpilot_053.model.primary_path_plan",
                path="simulations/flowpilot_053_ppa_maintenance_model.py",
                symbol="build_primary_path_plan",
                implements=("flowpilot_053.primary_path_authority_no_fallback",),
                external_outputs=("PrimaryPathAuthorityPlan",),
                error_paths=("fallback candidate masks primary failure",),
            ),
            _contract(
                "flowpilot_053.model.behavior_commitment_ledger",
                path="simulations/flowpilot_053_ppa_maintenance_model.py",
                symbol="build_behavior_commitment_ledger",
                implements=("flowpilot_053.behavior_commitments_cover_current_contract_promises",),
                external_inputs=("PrimaryPathAuthorityReport",),
                external_outputs=("BehaviorCommitmentLedger",),
                error_paths=("missing PPA handoff or stale evidence",),
            ),
            _contract(
                "flowpilot_053.model.field_lifecycle_plan",
                path="simulations/flowpilot_053_ppa_maintenance_model.py",
                symbol="build_field_lifecycle_plan",
                implements=("flowpilot_053.field_lifecycle_current_fields_no_compatibility",),
                external_outputs=("FieldLifecyclePlan",),
                error_paths=("behavior-bearing field lacks projection",),
            ),
            _contract(
                "flowpilot_053.model.risk_evidence_plan",
                path="simulations/flowpilot_053_ppa_maintenance_model.py",
                symbol="build_risk_evidence_ledger_plan",
                implements=("flowpilot_053.release_evidence_consumes_upgrade_and_ppa",),
                external_inputs=("PPA, BCL, and FieldLifecycle reports",),
                external_outputs=("RiskEvidenceLedgerPlan",),
                error_paths=("release claim has stale or routine-only proof",),
            ),
        ),
        test_evidence=(
            _evidence(
                "flowpilot_053.runner.all_gates",
                test_name="test_runner_consumes_real_flowguard_053_routes",
                path="tests/test_flowpilot_053_ppa_maintenance.py",
                command="python -m pytest tests/test_flowpilot_053_ppa_maintenance.py -q",
                test_kind=HAPPY,
                covers=(
                    "flowpilot_053.primary_path_authority_no_fallback",
                    "flowpilot_053.behavior_commitments_cover_current_contract_promises",
                    "flowpilot_053.field_lifecycle_current_fields_no_compatibility",
                    "flowpilot_053.release_evidence_consumes_upgrade_and_ppa",
                ),
                code_contracts=(
                    "flowpilot_053.runner.build_report",
                    "flowpilot_053.model.primary_path_plan",
                    "flowpilot_053.model.behavior_commitment_ledger",
                    "flowpilot_053.model.field_lifecycle_plan",
                    "flowpilot_053.model.risk_evidence_plan",
                ),
            ),
            _evidence(
                "flowpilot_053.negative.primary_path_authority",
                test_name="test_primary_path_authority_rejects_old_field_and_duplicate_primary_paths",
                path="tests/test_flowpilot_053_ppa_maintenance.py",
                command=(
                    "python -m pytest tests/test_flowpilot_053_ppa_maintenance.py "
                    "-k test_primary_path_authority_rejects_old_field_and_duplicate_primary_paths -q"
                ),
                test_kind=NEGATIVE,
                covers=("flowpilot_053.primary_path_authority_no_fallback",),
                code_contracts=("flowpilot_053.model.primary_path_plan",),
            ),
            _evidence(
                "flowpilot_053.negative.behavior_commitment",
                test_name="test_behavior_commitment_ledger_requires_ppa_and_current_evidence",
                path="tests/test_flowpilot_053_ppa_maintenance.py",
                command=(
                    "python -m pytest tests/test_flowpilot_053_ppa_maintenance.py "
                    "-k test_behavior_commitment_ledger_requires_ppa_and_current_evidence -q"
                ),
                test_kind=NEGATIVE,
                covers=("flowpilot_053.behavior_commitments_cover_current_contract_promises",),
                code_contracts=("flowpilot_053.model.behavior_commitment_ledger",),
            ),
            _evidence(
                "flowpilot_053.negative.field_lifecycle",
                test_name="test_field_lifecycle_covers_existing_fields_without_new_contract_fields",
                path="tests/test_flowpilot_053_ppa_maintenance.py",
                command=(
                    "python -m pytest tests/test_flowpilot_053_ppa_maintenance.py "
                    "-k test_field_lifecycle_covers_existing_fields_without_new_contract_fields -q"
                ),
                test_kind=NEGATIVE,
                covers=("flowpilot_053.field_lifecycle_current_fields_no_compatibility",),
                code_contracts=("flowpilot_053.model.field_lifecycle_plan",),
            ),
            _evidence(
                "flowpilot_053.replay.formal_ai_execution_closure",
                test_name="run_flowpilot_ai_response_execution_closure_checks",
                path="simulations/run_flowpilot_ai_response_execution_closure_checks.py",
                command=(
                    "python simulations/run_flowpilot_ai_response_execution_closure_checks.py "
                    "--mode adversarial --budget-seconds 3600 --json-out "
                    "tmp/test_results/formal_ai_submit_adversarial.json"
                ),
                test_kind=REPLAY,
                covers=(
                    "flowpilot_053.primary_path_authority_no_fallback",
                    "flowpilot_053.release_evidence_consumes_upgrade_and_ppa",
                ),
            ),
        ),
    )

    complete_workstream_resource_discovery = ModelTestAlignmentPlan(
        model_id="flowpilot_complete_workstream_resource_discovery",
        obligations=(
            _obligation(
                "complete_workstream.substantive_roles_plan_execute_verify_report",
                obligation_type="workflow",
                description=(
                    "PM, Worker, Reviewer, and FlowGuard Operator treat each assigned packet as a complete bounded workstream, "
                    "report numbered plan-step completion, integrate delegation, verify current evidence, and repair in-scope defects."
                ),
                required_test_kinds=(HAPPY, NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "complete_workstream.controller_foreground_only",
                obligation_type="authority",
                description="Controller follows the Runtime-derived foreground action ledger and never authors a substantive role plan.",
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "complete_workstream.reviewer_audit_pm_sub9_disposition",
                obligation_type="review",
                description=(
                    "Reviewer compares plan rows with actual artifacts, evidence, delegation, integration, verification, repair, and blockers; "
                    "PM explicitly dispositions every score below nine without Runtime auto-blocking it."
                ),
                required_test_kinds=(HAPPY, NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "resource_discovery.shallow_inventory_then_pm_selection",
                obligation_type="workflow",
                description=(
                    "Runtime performs one mandatory shallow local skill inventory, PM selects relevant candidates, and only selected skills are deep-read."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "resource_discovery.material_work_ordinary_special_path_removed",
                obligation_type="architecture_reduction",
                description=(
                    "Reading, research, experiment, source verification, and evidence synthesis use ordinary PM role work; old material fields, cards, "
                    "contracts, and sufficiency gates are deleted or rejected and an optional material map never blocks."
                ),
                required_test_kinds=(HAPPY, NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "complete_workstream.finite_fake_ai_execution_profiles",
                obligation_type="test_mesh",
                description=(
                    "Every declared complete-workstream and resource-discovery profile is generated from the current public checklist and executed through "
                    "the real submit/review/repair chain with declared, selected, executed, passed, failed, stale, and not-run accounting kept separate."
                ),
                required_test_kinds=(NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
        ),
        code_contracts=(
            _contract(
                "complete_workstream.role_handoff_instructions",
                path="skills/flowpilot/assets/flowpilot_core_runtime/role_handoff.py",
                symbol="SUBSTANTIVE_WORKSTREAM_INSTRUCTIONS",
                implements=(
                    "complete_workstream.substantive_roles_plan_execute_verify_report",
                    "complete_workstream.controller_foreground_only",
                ),
                external_inputs=("current packet and responsibility",),
                external_outputs=("role-specific current handoff instructions",),
                error_paths=("controller authority leakage", "substantive role quick-reply shortcut"),
            ),
            _contract(
                "complete_workstream.semantic_report_projection",
                path="skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py",
                symbol="workstream_plan_and_completion_example",
                implements=("complete_workstream.substantive_roles_plan_execute_verify_report",),
                external_outputs=("contract_self_check.workstream_plan_and_completion",),
                error_paths=("missing, vague, incomplete, stale, or contradictory plan report",),
            ),
            _contract(
                "complete_workstream.reviewer_window",
                path="skills/flowpilot/assets/flowpilot_core_runtime/review_window_contracts.py",
                symbol="review_window_contract_for_context",
                implements=("complete_workstream.reviewer_audit_pm_sub9_disposition",),
                external_inputs=("current subject result and review stage",),
                external_outputs=("Reviewer challenge and PM repair/disposition path",),
                error_paths=("self-report accepted without evidence", "sub9 score silently ignored"),
            ),
            _contract(
                "resource_discovery.runtime_local_inventory",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_runtime_local_capability_inventory",
                implements=("resource_discovery.shallow_inventory_then_pm_selection",),
                external_inputs=("current project and installed skill roots",),
                external_outputs=("packet-only shallow capability inventory",),
                error_paths=("missing inventory", "Runtime deep-reads or selects semantic relevance"),
            ),
            _contract(
                "resource_discovery.current_result_contract",
                path="skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
                symbol="_discovery_result_violation",
                implements=(
                    "resource_discovery.shallow_inventory_then_pm_selection",
                    "resource_discovery.material_work_ordinary_special_path_removed",
                ),
                external_inputs=("current task.discovery result",),
                external_outputs=("candidate skill selection or current-contract rejection",),
                error_paths=("material_sources", "material_sufficiency", "material_current"),
            ),
            _contract(
                "complete_workstream.canonical_fake_ai",
                path="simulations/flowpilot_contract_driven_fake_ai.py",
                symbol="ContractDrivenFakeAIResponder",
                implements=("complete_workstream.finite_fake_ai_execution_profiles",),
                external_inputs=("public open-packet current checklist",),
                external_outputs=("profile payload and real submit/review receipts",),
                error_paths=("private constructor authority", "generated-but-not-executed overclaim"),
            ),
        ),
        test_evidence=(
            _evidence(
                "complete_workstream.happy.shared_role_contract",
                test_name="test_runtime_handoff_projects_one_shared_workstream_contract_to_every_role",
                path="tests/test_flowpilot_complete_workstream_orchestration.py",
                command="python -m unittest tests.test_flowpilot_complete_workstream_orchestration",
                test_kind=HAPPY,
                covers=(
                    "complete_workstream.substantive_roles_plan_execute_verify_report",
                    "complete_workstream.controller_foreground_only",
                    "complete_workstream.reviewer_audit_pm_sub9_disposition",
                ),
                code_contracts=(
                    "complete_workstream.role_handoff_instructions",
                    "complete_workstream.semantic_report_projection",
                    "complete_workstream.reviewer_window",
                ),
            ),
            _evidence(
                "complete_workstream.negative.boundary_and_report",
                test_name="test_controller_has_no_substantive_plan_authority",
                path="tests/test_flowpilot_complete_workstream_orchestration.py",
                command="python -m unittest tests.test_flowpilot_complete_workstream_orchestration",
                test_kind=NEGATIVE,
                covers=(
                    "complete_workstream.substantive_roles_plan_execute_verify_report",
                    "complete_workstream.controller_foreground_only",
                    "complete_workstream.reviewer_audit_pm_sub9_disposition",
                ),
                code_contracts=(
                    "complete_workstream.role_handoff_instructions",
                    "complete_workstream.semantic_report_projection",
                    "complete_workstream.reviewer_window",
                ),
            ),
            _evidence(
                "resource_discovery.happy.current_inventory_and_ordinary_work",
                test_name="test_runtime_projects_current_shallow_local_inventory_before_pm_selection",
                path="tests/test_flowpilot_ordinary_resource_discovery.py",
                command="python -m unittest tests.test_flowpilot_ordinary_resource_discovery",
                test_kind=HAPPY,
                covers=(
                    "resource_discovery.shallow_inventory_then_pm_selection",
                    "resource_discovery.material_work_ordinary_special_path_removed",
                ),
                code_contracts=(
                    "resource_discovery.runtime_local_inventory",
                    "resource_discovery.current_result_contract",
                ),
            ),
            _evidence(
                "resource_discovery.negative.removed_material_surfaces",
                test_name="test_removed_material_discovery_fields_have_only_negative_or_historical_hits",
                path="tests/test_flowpilot_ordinary_resource_discovery.py",
                command="python -m unittest tests.test_flowpilot_ordinary_resource_discovery",
                test_kind=NEGATIVE,
                covers=(
                    "resource_discovery.shallow_inventory_then_pm_selection",
                    "resource_discovery.material_work_ordinary_special_path_removed",
                ),
                code_contracts=("resource_discovery.current_result_contract",),
            ),
            _evidence(
                "complete_workstream.replay.real_fake_ai_chain",
                test_name="test_every_workstream_profile_traverses_real_ack_open_submit_flowguard_reviewer_and_repair_routing",
                path="tests/test_flowpilot_complete_workstream_fake_ai.py",
                command="python -m unittest tests.test_flowpilot_complete_workstream_fake_ai",
                test_kind=REPLAY,
                covers=(
                    "complete_workstream.substantive_roles_plan_execute_verify_report",
                    "complete_workstream.reviewer_audit_pm_sub9_disposition",
                    "resource_discovery.material_work_ordinary_special_path_removed",
                    "complete_workstream.finite_fake_ai_execution_profiles",
                ),
                code_contracts=(
                    "complete_workstream.semantic_report_projection",
                    "complete_workstream.reviewer_window",
                    "resource_discovery.current_result_contract",
                    "complete_workstream.canonical_fake_ai",
                ),
            ),
            _evidence(
                "complete_workstream.negative.fake_ai_bad_profiles",
                test_name="test_resource_profiles_use_real_current_family_checklists_and_submit_paths",
                path="tests/test_flowpilot_complete_workstream_fake_ai.py",
                command="python -m unittest tests.test_flowpilot_complete_workstream_fake_ai",
                test_kind=NEGATIVE,
                covers=(
                    "complete_workstream.finite_fake_ai_execution_profiles",
                    "resource_discovery.material_work_ordinary_special_path_removed",
                ),
                code_contracts=("complete_workstream.canonical_fake_ai",),
            ),
        ),
    )

    skillguard_current_contract = ModelTestAlignmentPlan(
        model_id="skillguard_deep_contract_maintenance",
        obligations=(
            _obligation(
                "skillguard.current_v2_authority_is_singular",
                obligation_type="authority",
                description=(
                    "FlowPilot uses only the current SkillGuard V2 contract-source, compiled-contract, and check-manifest trio; "
                    "former V1 files and parallel SkillGuard runtime ownership are rejected."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "skillguard.current_model_refines_existing_flowpilot_stages",
                obligation_type="workflow",
                description=(
                    "The FlowGuard contract projection refines the existing opt-in, PM route-plan, complete-workstream, and "
                    "independent-closure stages without creating a second domain workflow."
                ),
                required_test_kinds=(HAPPY, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "skillguard.native_handoff_bindings_are_complete",
                obligation_type="authority",
                description=(
                    "Every existing FlowPilot route and declared check is explicitly bound to its native owner source; "
                    "missing route or check bindings block global selection instead of falling back."
                ),
                required_test_kinds=(HAPPY, NEGATIVE, REPLAY),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
            _obligation(
                "skillguard.final_receipt_is_read_only_current_consumer",
                obligation_type="evidence",
                description=(
                    "SkillGuard consumes the unique current final-confidence receipt without --background, --resume, "
                    "Scheduled Task, or any second execution owner."
                ),
                required_test_kinds=(HAPPY, NEGATIVE),
                allow_shared_evidence=True,
                allow_shared_implementation=True,
            ),
        ),
        code_contracts=(
            _contract(
                "skillguard.current_contract_source",
                path="skills/flowpilot/.skillguard/contract-source.json",
                symbol="schema_version",
                implements=(
                    "skillguard.current_v2_authority_is_singular",
                    "skillguard.current_model_refines_existing_flowpilot_stages",
                    "skillguard.native_handoff_bindings_are_complete",
                    "skillguard.final_receipt_is_read_only_current_consumer",
                ),
                external_inputs=("current FlowPilot stage owners and final17 receipt identity",),
                external_outputs=("one SkillGuard V2 declarative contract source",),
                error_paths=(
                    "former authority",
                    "parallel runtime route",
                    "missing native route binding",
                    "missing native check binding",
                    "stale or executable final consumer",
                ),
            ),
            _contract(
                "skillguard.flowguard_contract_projection",
                path="simulations/flowpilot_skillguard_contract_model.py",
                symbol="export_contract_model",
                implements=(
                    "skillguard.current_v2_authority_is_singular",
                    "skillguard.current_model_refines_existing_flowpilot_stages",
                    "skillguard.native_handoff_bindings_are_complete",
                ),
                external_inputs=("current FlowPilot activation, planning, workstream, and closure facts",),
                external_outputs=("four-route FlowGuard contract projection and ten obligations",),
                error_paths=(
                    "ordinary small task",
                    "missing native route binding",
                    "missing native check binding",
                    "missing role plan",
                    "unintegrated delegation",
                    "stale closure evidence",
                ),
            ),
            _contract(
                "skillguard.public_v2_contract_compiler",
                path="scripts/refresh_flowpilot_skillguard_contract.py",
                symbol="main",
                implements=("skillguard.current_v2_authority_is_singular",),
                external_inputs=("contract-source.json", "public SkillGuard V2 compiler and checkers"),
                external_outputs=("compiled-contract.json and check-manifest.json parity",),
                error_paths=("private API dependency", "generated authority drift", "former V1 regeneration"),
            ),
            _contract(
                "skillguard.focused_contract_runner",
                path="simulations/run_flowpilot_skillguard_contract_checks.py",
                symbol="run_checks",
                implements=(
                    "skillguard.current_v2_authority_is_singular",
                    "skillguard.current_model_refines_existing_flowpilot_stages",
                    "skillguard.native_handoff_bindings_are_complete",
                    "skillguard.final_receipt_is_read_only_current_consumer",
                ),
                external_inputs=("current contract source and FlowGuard model export",),
                external_outputs=("scenario, progress, conformance, and refinement report",),
                error_paths=("missing blocker", "non-monotonic closure", "route mismatch", "final receipt owner duplication"),
            ),
        ),
        test_evidence=(
            _evidence(
                "skillguard.happy.focused_contract_runner",
                test_name="test_focused_flowguard_runner_closes_scenarios_progress_and_refinement",
                path="tests/test_flowpilot_skillguard_deep_contract.py",
                command=(
                    "python -m unittest tests.test_flowpilot_skillguard_deep_contract."
                    "FlowPilotSkillGuardDeepContractTests."
                    "test_focused_flowguard_runner_closes_scenarios_progress_and_refinement"
                ),
                test_kind=HAPPY,
                covers=(
                    "skillguard.current_v2_authority_is_singular",
                    "skillguard.current_model_refines_existing_flowpilot_stages",
                    "skillguard.native_handoff_bindings_are_complete",
                    "skillguard.final_receipt_is_read_only_current_consumer",
                ),
                code_contracts=(
                    "skillguard.current_contract_source",
                    "skillguard.flowguard_contract_projection",
                    "skillguard.public_v2_contract_compiler",
                    "skillguard.focused_contract_runner",
                ),
            ),
            _evidence(
                "skillguard.negative.native_handoff_bindings",
                test_name="test_native_handoff_bindings_cover_every_existing_route_and_check",
                path="tests/test_flowpilot_skillguard_deep_contract.py",
                command=(
                    "python -m unittest tests.test_flowpilot_skillguard_deep_contract."
                    "FlowPilotSkillGuardDeepContractTests."
                    "test_native_handoff_bindings_cover_every_existing_route_and_check"
                ),
                test_kind=NEGATIVE,
                covers=("skillguard.native_handoff_bindings_are_complete",),
                code_contracts=(
                    "skillguard.current_contract_source",
                    "skillguard.flowguard_contract_projection",
                    "skillguard.focused_contract_runner",
                ),
            ),
            _evidence(
                "skillguard.negative.former_authority_removed",
                test_name="test_one_current_contract_trio_replaces_every_former_authority",
                path="tests/test_flowpilot_skillguard_deep_contract.py",
                command=(
                    "python -m unittest tests.test_flowpilot_skillguard_deep_contract."
                    "FlowPilotSkillGuardDeepContractTests."
                    "test_one_current_contract_trio_replaces_every_former_authority"
                ),
                test_kind=NEGATIVE,
                covers=("skillguard.current_v2_authority_is_singular",),
                code_contracts=(
                    "skillguard.current_contract_source",
                    "skillguard.public_v2_contract_compiler",
                ),
            ),
            _evidence(
                "skillguard.replay.four_existing_stage_owners",
                test_name="test_exported_flowguard_model_covers_the_four_existing_stage_owners",
                path="tests/test_flowpilot_skillguard_deep_contract.py",
                command=(
                    "python -m unittest tests.test_flowpilot_skillguard_deep_contract."
                    "FlowPilotSkillGuardDeepContractTests."
                    "test_exported_flowguard_model_covers_the_four_existing_stage_owners"
                ),
                test_kind=REPLAY,
                covers=(
                    "skillguard.current_model_refines_existing_flowpilot_stages",
                    "skillguard.native_handoff_bindings_are_complete",
                ),
                code_contracts=("skillguard.flowguard_contract_projection",),
            ),
            _evidence(
                "skillguard.negative.final_receipt_consumer",
                test_name="test_final_receipt_check_is_a_read_only_consumer_not_a_second_owner",
                path="tests/test_flowpilot_skillguard_deep_contract.py",
                command=(
                    "python -m unittest tests.test_flowpilot_skillguard_deep_contract."
                    "FlowPilotSkillGuardDeepContractTests."
                    "test_final_receipt_check_is_a_read_only_consumer_not_a_second_owner"
                ),
                test_kind=NEGATIVE,
                covers=("skillguard.final_receipt_is_read_only_current_consumer",),
                code_contracts=(
                    "skillguard.current_contract_source",
                    "skillguard.focused_contract_runner",
                ),
            ),
        ),
    )

    startup = _with_runtime_path(startup, "startup")
    packet_card_ack = _with_runtime_path(packet_card_ack, "packet/card/ack")
    packet_result_family = _with_runtime_path(packet_result_family, "packet result family")
    route_mutation = _with_runtime_path(route_mutation, "route mutation")
    unified_repair_integrity = _with_runtime_path(
        unified_repair_integrity,
        "unified historical and terminal repair integrity",
    )
    currentness_field_lifecycle = _with_runtime_path(currentness_field_lifecycle, "field lifecycle currentness")
    current_node_trunk = _with_runtime_path(current_node_trunk, "current-node trunk invariant")
    terminal_closure_resume = _with_runtime_path(terminal_closure_resume, "terminal/closure/resume")
    role_output = _with_runtime_path(role_output, "role/output contracts")
    router_loop_daemon = _with_runtime_path(router_loop_daemon, "router loop/daemon")
    repair_transactions = _with_runtime_path(repair_transactions, "repair transactions")
    tiering = _with_runtime_path(tiering, "test tiering/slow-test contracts")
    rejection_liveness = _with_runtime_path(rejection_liveness, "rejection/liveness matrix")
    route_authority = _with_runtime_path(route_authority, "route authority singularity")
    core_deliverable = _with_runtime_path(core_deliverable, "core deliverable non-downgrade")
    flowguard_053_ppa_maintenance = _with_runtime_path(
        flowguard_053_ppa_maintenance,
        "flowguard 0.53 ppa maintenance",
    )
    complete_workstream_resource_discovery = _with_runtime_path(
        complete_workstream_resource_discovery,
        "complete workstream and ordinary resource discovery",
    )
    skillguard_current_contract = _with_runtime_path(
        skillguard_current_contract,
        "skillguard current contract maintenance",
    )
    meta_capability = _with_runtime_path(meta_capability, "meta/capability parents")

    return [
        _plan_entry(
            "startup",
            startup,
            model_checks=(
                "python simulations/run_flowpilot_startup_control_checks.py",
                "python simulations/run_flowpilot_deterministic_startup_bootstrap_checks.py",
            ),
            coverage_boundary="Startup alignment covers ordinary runtime and unit tests for the startup gate. It does not rerun UI smoke or long parent graphs.",
        ),
        _plan_entry(
            "packet/card/ack",
            packet_card_ack,
            model_checks=(
                "python simulations/run_flowpilot_packet_lifecycle_checks.py",
                "python simulations/run_flowpilot_card_envelope_checks.py",
                "python simulations/run_flowpilot_event_contract_checks.py",
                "python skills/flowpilot/assets/run_packet_control_plane_checks.py",
            ),
            coverage_boundary="Packet/card/ACK alignment covers mechanical handoff, identity, hash, receipt, and ACK/return hazards. It does not treat ACK as semantic role approval.",
        ),
        _plan_entry(
            "packet result family",
            packet_result_family,
            model_checks=(
                "python simulations/run_flowpilot_packet_result_family_parity_checks.py",
                "python simulations/run_flowpilot_fake_ai_runtime_replay_checks.py --json-out simulations/flowpilot_fake_ai_runtime_replay_summary.json",
                "python simulations/run_flowpilot_real_issue_backfeed_checks.py --json-out simulations/flowpilot_real_issue_backfeed_results.json",
            ),
            coverage_boundary="Packet-result family alignment covers durable-envelope reconciliation, AI-facing result contracts, fake-AI runtime replay, and real-issue backfeed ownership. It does not inspect sealed result bodies or replace PM semantic review.",
        ),
        _plan_entry(
            "route mutation",
            route_mutation,
            model_checks=("python simulations/run_flowpilot_route_mutation_activation_checks.py",),
            coverage_boundary="Route-mutation alignment covers activation preconditions, sibling replacement, stale evidence, and route-sign projection for ordinary tests.",
        ),
        _plan_entry(
            "unified historical and terminal repair integrity",
            unified_repair_integrity,
            model_checks=(
                "python simulations/run_flowpilot_unified_repair_integrity_checks.py --json-out simulations/flowpilot_unified_repair_integrity_results.json",
            ),
            coverage_boundary=(
                "This declaration aligns PM-proactive historical repair and terminal backward-replay repair to one "
                "same-slot replacement engine, one Worker -> FlowGuard -> Reviewer evidence chain, current repair "
                "generations, the staged PM-decision gate before effect commit/Worker dispatch, route-member "
                "conservation, repair-child closure projection, same-slot affected replay, repeated lineage, "
                "explicit model-action/runtime-decision refinement, and the three-round "
                "terminal cap. Each obligation is bound to a real current ordinary runtime regression; the "
                "model runner remains separate and is never substituted for ordinary TestEvidence."
            ),
        ),
        _plan_entry(
            "field lifecycle currentness",
            currentness_field_lifecycle,
            model_checks=(
                "python simulations/run_flowpilot_field_mesh_checks.py",
                "python simulations/run_flowpilot_field_contract_checks.py",
            ),
            coverage_boundary=(
                "Field lifecycle currentness alignment covers packet/result/frontier "
                "transition semantics and derived active-packet projections. It is "
                "current-contract only and does not accept legacy packet shapes."
            ),
        ),
        _plan_entry(
            "current-node trunk invariant",
            current_node_trunk,
            model_checks=("python simulations/run_flowpilot_prework_flowguard_gate_checks.py",),
            coverage_boundary=(
                "Current-node trunk alignment names ordinary node plan Reviewer "
                "-> Worker -> post-result FlowGuard -> independent Reviewer, "
                "plus structural route FlowGuard -> PM absorption -> Reviewer "
                "before route mutation commit. It binds the focused route-gate "
                "model to high-standard runtime tests, but it does not replace "
                "semantic review of the worker output or PM route decisions."
            ),
        ),
        _plan_entry(
            "terminal/closure/resume",
            terminal_closure_resume,
            model_checks=(
                "python simulations/run_flowpilot_runtime_closure_checks.py",
                "python simulations/run_flowpilot_recursive_closure_reconciliation_checks.py",
                "python simulations/run_flowpilot_resume_checks.py",
            ),
            coverage_boundary="Terminal, closure, and resume alignment covers runtime tests for ledger closure and re-entry. It is not a production replay adapter.",
        ),
        _plan_entry(
            "role/output contracts",
            role_output,
            model_checks=(
                "python simulations/run_output_contract_checks.py",
                "python simulations/run_flowpilot_role_output_runtime_checks.py",
            ),
            coverage_boundary="Role/output alignment covers mechanical role-output and packet-output contracts. It does not judge task semantic quality.",
        ),
        _plan_entry(
            "router loop/daemon",
            router_loop_daemon,
            model_checks=(
                "python simulations/run_flowpilot_router_loop_checks.py",
                "python simulations/run_flowpilot_persistent_router_daemon_checks.py",
                "python simulations/run_flowpilot_daemon_startup_lock_checks.py",
                "python simulations/run_flowpilot_daemon_controller_actions_checks.py",
                "python simulations/run_flowpilot_daemon_wait_liveness_checks.py",
                "python simulations/run_flowpilot_daemon_terminal_projection_checks.py",
            ),
            coverage_boundary="Router-loop/daemon alignment covers foreground unit/runtime tests for queue, lock, and packet-loop behavior. It does not run long daemon soak tests.",
        ),
        _plan_entry(
            "repair transactions",
            repair_transactions,
            model_checks=("python simulations/run_flowpilot_repair_transaction_checks.py",),
            coverage_boundary="Repair-transaction alignment covers executable producer/action/handler/stop evidence and focused material-dispatch stale-wait regressions. It does not prove semantic quality of replacement packet contents.",
        ),
        _plan_entry(
            "test tiering/slow-test contracts",
            tiering,
            model_checks=(
                "python simulations/run_flowpilot_test_tiering_checks.py",
                "python simulations/run_flowpilot_slow_test_contract_checks.py",
            ),
            coverage_boundary="Test-tiering alignment covers test-plan mechanics and slow-test parent/child contracts, including progress-only background hazards.",
        ),
        _plan_entry(
            "rejection/liveness matrix",
            rejection_liveness,
            model_checks=(
                "python simulations/run_flowpilot_rejection_liveness_matrix_checks.py --json-out simulations/flowpilot_rejection_liveness_matrix_results.json",
                "python simulations/flowpilot_synthetic_agent_coverage_matrix.py --declaration-only --json-out tmp/test_results/flowpilot_synthetic_agent_coverage_matrix_declaration.json",
            ),
            coverage_boundary=(
                "Rejection/liveness alignment covers malformed current-contract packets, "
                "fake-AI no-delta retries, stuck absorption, and live repeated-action "
                "projection. Synthetic rows prove control flow only and never claim live "
                "semantic completion."
            ),
        ),
        _plan_entry(
            "route authority singularity",
            route_authority,
            model_checks=(
                "python simulations/run_flowpilot_route_authority_singularity_checks.py --json-out simulations/flowpilot_route_authority_singularity_results.json",
                "python simulations/run_flowpilot_model_mesh_checks.py --json-out simulations/flowpilot_model_mesh_results.json",
            ),
            coverage_boundary=(
                "Route-authority alignment covers current legal-action ownership, "
                "wrong-path/alias/fallback rejection, required repair-command "
                "feedback, corrected retry behavior, and ModelMesh parent hazards. "
                "Synthetic replay proves control flow only and cannot claim live "
                "semantic completion."
            ),
        ),
        _plan_entry(
            "core deliverable non-downgrade",
            core_deliverable,
            model_checks=(
                "python -m unittest tests.test_flowpilot_card_instruction_coverage.FlowPilotCardInstructionCoverageTests.test_prompt_first_quality_chain_preserves_source_intent_without_runtime_semantic_gate",
                "python -m unittest tests.test_flowpilot_synthetic_agent_trace_replay.FlowPilotSyntheticAgentTraceReplayTests.test_core_deliverable_downgrade_chain_blocks_completion",
                "python simulations/flowpilot_synthetic_agent_coverage_matrix.py --declaration-only --json-out tmp/test_results/flowpilot_synthetic_agent_coverage_matrix_declaration.json",
            ),
            coverage_boundary=(
                "Core-deliverable non-downgrade alignment covers prompt-card standards "
                "and synthetic bad-chain replay. It proves rejection and repair routing "
                "for substitute completion claims, not live semantic completion."
            ),
        ),
        _plan_entry(
            "flowguard 0.53 ppa maintenance",
            flowguard_053_ppa_maintenance,
            model_checks=(
                "python simulations/run_flowpilot_053_ppa_maintenance_checks.py --json-out simulations/flowpilot_053_ppa_maintenance_results.json",
                "python -m pytest tests/test_flowpilot_053_ppa_maintenance.py -q",
            ),
            coverage_boundary=(
                "FlowGuard 0.53 PPA maintenance alignment covers current-contract "
                "no-fallback commitments, field lifecycle ownership, risk gates, "
                "and release-evidence freshness. It does not add runtime fields, "
                "compatibility aliases, or semantic runtime review."
            ),
        ),
        _plan_entry(
            "complete workstream and ordinary resource discovery",
            complete_workstream_resource_discovery,
            model_checks=(
                "python simulations/run_flowpilot_complete_workstream_orchestration_checks.py",
                "python simulations/run_flowpilot_ordinary_resource_discovery_checks.py",
                "python -m unittest tests.test_flowpilot_complete_workstream_orchestration tests.test_flowpilot_ordinary_resource_discovery tests.test_flowpilot_complete_workstream_fake_ai",
            ),
            coverage_boundary=(
                "This family aligns the shared role plan/report contract, Controller exclusion, Reviewer/PM semantic audit, "
                "mandatory shallow skill inventory, ordinary material work, deleted material-special surfaces, and real canonical fake-AI replay. "
                "It does not turn semantic quality into a Runtime mechanical score or create a second material workflow."
            ),
        ),
        _plan_entry(
            "skillguard deep contract maintenance",
            skillguard_current_contract,
            model_checks=(
                "python simulations/run_flowpilot_skillguard_contract_checks.py --json-out simulations/flowpilot_skillguard_current_contract_results.json",
                "python scripts/refresh_flowpilot_skillguard_contract.py --check",
                "python -m unittest tests.test_flowpilot_skillguard_deep_contract",
            ),
            coverage_boundary=(
                "This family aligns the current declarative SkillGuard V2 target, its four existing FlowPilot stage owners, "
                "public compiler parity, known-bad rejection, and the read-only final17 receipt consumer. It does not add a "
                "SkillGuard runtime route or prove arbitrary AI execution depth."
            ),
        ),
        _plan_entry(
            "meta/capability parents",
            meta_capability,
            model_checks=(
                "python simulations/run_meta_checks.py",
                "python simulations/run_capability_checks.py",
                "python simulations/run_meta_checks.py --full --fast",
                "python simulations/run_capability_checks.py --full --fast",
            ),
            coverage_boundary="Meta/Capability alignment covers parent-runner proof boundaries and control-gate unit evidence only. Parent results remain abstract model confidence, not ordinary production conformance.",
        ),
    ]
